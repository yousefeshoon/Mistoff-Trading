# mt5_importer.py

import pandas as pd
import db_manager
import os
from datetime import datetime
import re 
from decimal import Decimal, InvalidOperation 
import pytz # برای کار با تایم زون ها

def _clean_numeric_value(value):
    """
    مقادیر رشته‌ای را پاکسازی کرده و به Decimal تبدیل می‌کند.
    اگر نتواند به Decimal تبدیل کند، None برمی‌گرداند.
    """
    if pd.isna(value) or str(value).strip() == '':
        return None
    
    s_value = str(value).strip().replace('\xa0', '').replace(',', '')

    if '/' in s_value:
        parts = s_value.split('/')
        try:
            result = Decimal(parts[0].strip())
            return result
        except InvalidOperation:
            # print(f"DEBUG: InvalidOperation for value '{s_value}' in _clean_numeric_value (division part).")
            return None
    
    try:
        result = Decimal(s_value)
        return result
    except InvalidOperation:
        # print(f"DEBUG: InvalidOperation for value '{s_value}' in _clean_numeric_value.")
        return None

def process_mt5_report_for_preview(file_path):
    """
    تریدهای اکسل (یا CSV صادر شده از اکسل) متاتریدر 5 را می‌خواند، داده‌های اولیه را پردازش کرده
    و یک لیست از تریدهای آماده برای ورود و آمار مربوطه را برمی‌گرداند،
    بدون اینکه آنها را به دیتابیس اضافه کند.
    زمان‌ها به UTC تبدیل و در لیست آماده‌سازی می‌شوند.
    """
    prepared_trades_list = []
    total_trades_in_file = 0
    duplicate_count = 0
    skipped_error_count = 0

    # print(f"--- شروع پردازش فایل: {file_path} ---") 

    try:
        df_raw = pd.read_excel(file_path, header=6, engine='openpyxl')
        # print(f"DEBUG: فایل با موفقیت خوانده شد. ابعاد اولیه: {df_raw.shape}")
        
        # حذف ستون 'Unnamed: 13' اگر وجود داشته باشد
        if 'Unnamed: 13' in df_raw.columns:
            df_raw = df_raw.drop(columns=['Unnamed: 13'])
            # print("DEBUG: ستون 'Unnamed: 13' حذف شد.")

        # تغییر نام ستون‌ها برای خوانایی بهتر و استانداردسازی
        column_map = {
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
            'Profit': 'profit_amount_raw' 
        }

        df_processed = df_raw.rename(columns=column_map)
        # print(f"DEBUG: ستون‌ها تغییر نام یافتند. ستون‌ها بعد از تغییر نام: {df_processed.columns.tolist()}")

        # حذف ستون‌های نامربوت
        df_processed = df_processed.drop(columns=[
            'stop_loss_raw', 'take_profit_raw', 
            'commission_raw', 'swap_raw'
        ], errors='ignore') 
        # print("DEBUG: ستون‌های اضافی حذف شدند.")
        
        total_trades_in_file = len(df_processed) 
        # print(f"DEBUG: تعداد کل ردیف‌ها بعد از خواندن و حذف ستون‌های اولیه: {total_trades_in_file}")

        # ----------------------------------------------------------------------
        # بخش: اعمال فیلتر برای فقط رکوردهای Positions بسته شده (Closed Positions)
        # این فیلترها باید دقیق‌تر باشند تا Order ها یا رویدادهای دیگر را حذف کنند.
        # یک Position بسته شده باید دارای:
        # 1. Position ID (عددی)
        # 2. Symbol
        # 3. Open Time (Time)
        # 4. Close Time (Time.1)
        # 5. Exit Price (Price.1)
        # 6. Profit (عددی)
        # باشد و Trade Type آن نباید شامل کلمات مربوط به Order ها باشد.
        # ----------------------------------------------------------------------
        
        initial_rows_before_all_filters = len(df_processed)

        # فیلتر 1: Position ID باید عددی باشد و خالی نباشد.
        df_processed['position_id_numeric'] = pd.to_numeric(df_processed['position_id'], errors='coerce')
        df_filtered = df_processed[df_processed['position_id_numeric'].notna()].copy()
        df_filtered = df_filtered.drop(columns=['position_id_numeric'])
        # print(f"DEBUG: تعداد ردیف‌ها بعد از فیلتر Position ID عددی: {len(df_filtered)} (رد شده در این فاز: {initial_rows_before_all_filters - len(df_filtered)})")


        # فیلتر 2: Symbol نباید خالی باشد.
        initial_len_after_pos_filter = len(df_filtered)
        if 'symbol' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['symbol'].notna()].copy()
        # print(f"DEBUG: تعداد ردیف‌ها بعد از فیلتر Symbol خالی: {len(df_filtered)} (رد شده در این فاز: {initial_len_after_pos_filter - len(df_filtered)})")
        
        # فیلتر 3: بررسی وجود و غیر خالی بودن close_time_raw (Time.1) و exit_price_raw (Price.1)
        # این مهمترین فیلتر برای تشخیص Position بسته شده است.
        initial_len_after_symbol_filter = len(df_filtered)
        if 'close_time_raw' in df_filtered.columns and 'exit_price_raw' in df_filtered.columns:
            df_filtered = df_filtered[
                df_filtered['close_time_raw'].notna() & (df_filtered['close_time_raw'].astype(str).str.strip() != '') &
                df_filtered['exit_price_raw'].notna() & (df_filtered['exit_price_raw'].astype(str).str.strip() != '')
            ].copy()
        # print(f"DEBUG: تعداد ردیف‌ها بعد از فیلتر Close Time و Exit Price: {len(df_filtered)} (رد شده در این فاز: {initial_len_after_symbol_filter - len(df_filtered)})")


        # فیلتر 4: Profit باید یک مقدار عددی باشد.
        # این کمک میکنه ردیف‌هایی که Profit متنی دارن (مثل 'in' یا 'out' یا خالی) حذف بشن.
        initial_len_after_close_filter = len(df_filtered)
        df_filtered['profit_amount_numeric'] = df_filtered['profit_amount_raw'].apply(_clean_numeric_value)
        df_filtered = df_filtered[df_filtered['profit_amount_numeric'].notna()].copy()
        df_filtered = df_filtered.drop(columns=['profit_amount_numeric'])
        # print(f"DEBUG: تعداد ردیف‌ها بعد از فیلتر Profit عددی: {len(df_filtered)} (رد شده در این فاز: {initial_len_after_close_filter - len(df_filtered)})")


        # فیلتر 5: Trade Type نباید شامل کلمات کلیدی مربوط به Order ها یا رویدادها باشد.
        # این فیلتر حالا بعد از فیلتر Profit عددی اعمال میشه که کارایی بیشتری داره.
        initial_len_after_profit_filter = len(df_filtered)
        keywords_to_ignore_in_trade_type = ['limit', 'filled', 'in', 'out', 'market', 'canceled', 'modify', 'delete', 'buy limit', 'sell limit', 'buy stop', 'sell stop', 'close by'] 
        
        if 'trade_type' in df_filtered.columns:
            mask_to_keep_trade_type = ~df_filtered['trade_type'].astype(str).str.contains('|'.join(keywords_to_ignore_in_trade_type), case=False, na=False)
            df_final_positions = df_filtered[mask_to_keep_trade_type].copy()
        else:
            df_final_positions = df_filtered.copy()
        
        skipped_error_count += (initial_rows_before_all_filters - len(df_final_positions))
        # print(f"DEBUG: تعداد ردیف‌ها بعد از فیلتر کلمات کلیدی در 'trade_type' (نهایی): {len(df_final_positions)} (رد شده در این فاز: {initial_len_after_profit_filter - len(df_final_positions)})")

        # تعریف تایم زون مبدأ برای گزارش MT5 (معمولاً UTC+3:00)
        mt5_source_timezone = pytz.timezone('Etc/GMT-3') # UTC+3:00

        # print(f"DEBUG: {len(df_final_positions)} ردیف وارد حلقه پردازش نهایی می‌شوند.") 

        for index, row in df_final_positions.iterrows():
            row_skipped = False
            position_id_debug = "N/A" 
            try:
                position_id_debug = str(row.get('position_id', 'N/A')).strip() 
                
                position_id = str(int(float(position_id_debug))).strip() 
                
                # بررسی تکراری بودن در دیتابیس خودمان
                if db_manager.check_duplicate_trade(position_id=position_id):
                    row_skipped = True
                    duplicate_count += 1
                    # print(f"DEBUG_SKIP: ترید تکراری برای Position ID {position_id_debug}. سطر رد شد.") 
                    continue
                
                open_time_str = str(row.get('open_time_raw', '')).strip()
                # این بررسی‌ها در فیلترهای DataFrame انجام شده، اما برای اطمینان مجدد
                if not open_time_str:
                    row_skipped = True
                    continue

                # تلاش برای تبدیل تاریخ و زمان با فرمت‌های مختلف
                open_dt_obj_naive = None
                # فرمت‌های احتمالی MT5: YYYY.MM.DD HH:MM:SS یا YYYY.MM.DD HH:MM
                # همچنین ممکنه با خط تیره باشه
                date_formats = ['%Y.%m.%d %H:%M:%S', '%Y.%m.%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']
                for fmt in date_formats:
                    try:
                        open_dt_obj_naive = datetime.strptime(open_time_str, fmt)
                        break 
                    except ValueError:
                        continue 

                if open_dt_obj_naive is None:
                    # print(f"DEBUG_SKIP: فرمت زمان باز شدن نامعتبر برای Position ID {position_id_debug}: '{open_time_str}'. سطر رد شد.") 
                    row_skipped = True
                    continue 
                
                # زمان naive رو به تایم زون مبدأ MT5 آگاه می‌کنیم
                aware_dt_obj = mt5_source_timezone.localize(open_dt_obj_naive, is_dst=None) 
                
                # تبدیل به UTC برای ذخیره در دیتابیس
                utc_dt_obj = aware_dt_obj.astimezone(pytz.utc)

                trade_date = utc_dt_obj.strftime('%Y-%m-%d')
                trade_time = utc_dt_obj.strftime('%H:%M')

                symbol = str(row.get('symbol', '')).strip()
                if not symbol:
                    row_skipped = True
                    continue

                trade_type = str(row.get('trade_type', '')).strip()

                size_raw_val = str(row.get('size_raw', '')).strip()
                size = _clean_numeric_value(size_raw_val)
                if size is None:
                    row_skipped = True
                    continue
                
                entry_price_raw_val = str(row.get('entry_price_raw', '')).strip()
                entry_price = _clean_numeric_value(entry_price_raw_val)
                if entry_price is None:
                    row_skipped = True
                    continue

                exit_price_raw_val = str(row.get('exit_price_raw', '')).strip()
                exit_price = _clean_numeric_value(exit_price_raw_val)
                if exit_price is None:
                    row_skipped = True
                    continue

                profit_amount_raw_val = str(row.get('profit_amount_raw', '')).strip()
                profit_amount = _clean_numeric_value(profit_amount_raw_val)
                if profit_amount is None:
                    row_skipped = True
                    continue
                
                # منطق Profit/Loss
                profit_type = "RF"
                if profit_amount < 0:
                    profit_type = "Loss"
                elif profit_amount > 0:
                    profit_type = "Profit"
                
                errors_field = "" 

                prepared_trades_list.append({
                    'date': trade_date, # زمان UTC
                    'time': trade_time, # زمان UTC
                    'symbol': symbol,
                    'entry': entry_price,
                    'exit': exit_price,
                    'profit': profit_type,
                    'errors': errors_field,
                    'size': size,
                    'position_id': position_id,
                    'trade_type': trade_type,
                    'original_timezone': mt5_source_timezone.zone # ذخیره نام تایم زون مبدا MT5
                })

            except KeyError as ke:
                # print(f"DEBUG_SKIP_KEYERROR: ستون '{ke}' برای Position ID {position_id_debug} در ردیف پیدا نشد. سطر رد شد. (Index: {index})")
                row_skipped = True
                continue
            except Exception as e:
                # print(f"DEBUG_SKIP_UNEXPECTED: خطای ناشناخته در پردازش سطر برای Position ID {position_id_debug}: {e}. سطر رد شد. (Index: {index})")
                row_skipped = True
                continue
            finally:
                if row_skipped:
                    skipped_error_count += 1

        # print(f"--- پایان پردازش ---") 
        # print(f"DEBUG: تعداد کل ردیف‌های فایل (خام): {total_trades_in_file}")
        # print(f"DEBUG: تعداد ردیف‌های بعد از فیلترهای پاندا (آماده برای حلقه): {len(df_final_positions)}")
        # print(f"DEBUG: تعداد تریدهای جدید آماده برای ورود: {len(prepared_trades_list)}")
        # print(f"DEBUG: تعداد تریدهای تکراری (قبلاً در دیتابیس): {duplicate_count}")
        # print(f"DEBUG: تعداد ردیف‌های رد شده به دلیل خطا یا فیلتر (در حلقه): {skipped_error_count - (total_trades_in_file - len(df_final_positions))}") # فقط خطاهای حلقه را محاسبه میکند
        # print(f"DEBUG: تعداد کل ردیف‌های رد شده (شامل فیلترهای پاندا و خطاهای حلقه): {skipped_error_count}")


        return prepared_trades_list, total_trades_in_file, duplicate_count, skipped_error_count

    except FileNotFoundError:
        print(f"خطا: فایل '{file_path}' پیدا نشد. لطفاً مطمئن شوید فایل در مسیر صحیح قرار دارد.") 
        return [], 0, 0, 0
    except pd.errors.EmptyDataError:
        print(f"خطا: فایل '{file_path}' خالی است یا فرمت آن صحیح نیست.") 
        return [], 0, 0, 0
    except Exception as e:
        print(f"خطای بحرانی در حین خواندن یا پردازش فایل Excel/CSV: {e}") 
        return [], 0, 0, 0

def add_prepared_trades_to_db(trades_list):
    """
    لیستی از تریدهای آماده را به دیتابیس اضافه می‌کند.
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
            trade_type=trade_data['trade_type'],
            original_timezone_name=trade_data['original_timezone'] 
        ):
            imported_count += 1
        else:
            # print(f"DEBUG: Failed to add trade: {trade_data.get('position_id', 'N/A')}")
            pass
    return imported_count


if __name__ == "__main__":
    db_manager.migrate_database()
    
    test_file_path = "ReportHistory-303941.xlsx" 
    if os.path.exists(test_file_path):
        # print(f"در حال پردازش فایل تستی Excel/CSV: {test_file_path}") 
        prepared_trades, total, dup, err = process_mt5_report_for_preview(test_file_path)
        print(f"\n--- نتایج پیش‌نمایش از فایل ---") 
        print(f"کل تریدها در فایل (خام): {total}") 
        print(f"تعداد تریدهای جدید آماده برای ورود: {len(prepared_trades)}") 
        print(f"تعداد تریدهای تکراری (قبلاً در دیتابیس): {dup}") 
        print(f"تعداد ردیف‌های رد شده (کل): {err}") 
        
        if prepared_trades:
            print("\n--- 5 ترید اول آماده برای ورود: ---") 
            for i, trade in enumerate(prepared_trades[:5]):
                print(f"ترید {i+1}:") 
                for key, value in trade.items():
                    print(f"  {key}: {value}") 
                print("-" * 20) 
        else:
            print("هیچ تریدی برای وارد کردن پیدا نشد.") 

    else:
        print(f"فایل تستی با نام '{test_file_path}' پیدا نشد. لطفاً آن را در کنار اسکریپت قرار دهید یا مسیر درست را وارد کنید.")