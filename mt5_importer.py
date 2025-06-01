import pandas as pd
import db_manager
import os
from datetime import datetime, timedelta
import re 
from decimal import Decimal, InvalidOperation 

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
            return None
    
    try:
        result = Decimal(s_value)
        return result
    except InvalidOperation:
        return None

# تابع جدید برای پیش‌نمایش و پردازش اولیه گزارش MT5 بدون ذخیره در دیتابیس
def process_mt5_report_for_preview(file_path):
    """
    تریدهای اکسل (یا CSV صادر شده از اکسل) متاتریدر 5 را می‌خواند، داده‌های اولیه را پردازش کرده
    و یک لیست از تریدهای آماده برای ورود و آمار مربوطه را برمی‌گرداند،
    بدون اینکه آنها را به دیتابیس اضافه کند.
    """
    prepared_trades_list = []
    total_trades_in_file = 0
    duplicate_count = 0
    skipped_error_count = 0

    print(f"--- شروع پردازش فایل: {file_path} ---") #

    try:
        # 1. فایل Excel/CSV را با pandas.read_excel می‌خوانیم
        # header=6 به معنی استفاده از سطر هفتم (ایندکس 6) به عنوان سربرگ است.
        # engine='openpyxl' برای اطمینان از خواندن فایل‌های .xlsx
        df_raw = pd.read_excel(file_path, header=6, engine='openpyxl')
        
        # print(f"فایل با موفقیت خوانده شد. ابعاد اولیه: {df_raw.shape}") #
        
        # حذف ستون 'Unnamed: 13' اگر وجود داشته باشد (اغلب در خروجی‌های MT5 دیده می‌شود)
        if 'Unnamed: 13' in df_raw.columns:
            df_raw = df_raw.drop(columns=['Unnamed: 13'])
            # print("ستون 'Unnamed: 13' حذف شد.") #

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
        # print("ستون‌ها تغییر نام یافتند.") #

        # حذف ستون‌های نامربوت
        df_processed = df_processed.drop(columns=[
            'stop_loss_raw', 'take_profit_raw', 
            'commission_raw', 'swap_raw'
        ], errors='ignore') 
        # print("ستون‌های اضافی حذف شدند.") #
        
        total_trades_in_file = len(df_processed) 
        # print(f"تعداد کل ردیف‌ها بعد از خواندن و حذف ستون‌ها: {total_trades_in_file}") #

        # ----------------------------------------------------------------------
        # بخش: اعمال فیلتر برای فقط رکوردهای Positions (اولیه)
        # ----------------------------------------------------------------------
        initial_rows_before_pos_filter = len(df_processed)
        df_processed['position_id_numeric'] = pd.to_numeric(df_processed['position_id'], errors='coerce')
        df_processed = df_processed[df_processed['position_id_numeric'].notna()]
        df_processed = df_processed.drop(columns=['position_id_numeric'])
        skipped_error_count += (initial_rows_before_pos_filter - len(df_processed))
        # print(f"تعداد ردیف‌ها بعد از فیلتر Position ID عددی: {len(df_processed)} (رد شده: {skipped_error_count})") #


        if 'symbol' in df_processed.columns:
            initial_rows_before_symbol_filter = len(df_processed)
            df_processed = df_processed[df_processed['symbol'].notna()]
            skipped_error_count += (initial_rows_before_symbol_filter - len(df_processed))
            # print(f"تعداد ردیف‌ها بعد از فیلتر Symbol خالی: {len(df_processed)} (رد شده کلی: {skipped_error_count})") #


        # ----------------------------------------------------------------------
        # بخش: اعمال فیلتر بر اساس کلمات کلیدی (فقط در ستون 'trade_type')
        # ----------------------------------------------------------------------
        initial_rows_before_keyword_filter = len(df_processed)
        keywords_to_ignore = ['limit', 'filled', 'in', 'out', 'market', 'canceled'] 
        
        if 'trade_type' in df_processed.columns:
            mask_to_keep_trade_type = ~df_processed['trade_type'].astype(str).str.contains('|'.join(keywords_to_ignore), case=False, na=False)
            df_final_positions = df_processed[mask_to_keep_trade_type].copy()
        else:
            df_final_positions = df_processed.copy()

        skipped_error_count += (initial_rows_before_keyword_filter - len(df_final_positions))
        # print(f"تعداد ردیف‌ها بعد از فیلتر کلمات کلیدی (فقط 'trade_type'): {len(df_final_positions)} (رد شده کلی: {skipped_error_count})") #


        # ----------------------------------------------------------------------
        # پردازش نهایی و آماده‌سازی برای خروجی
        # ----------------------------------------------------------------------
        
        # print(f"DEBUG: {len(df_final_positions)} ردیف وارد حلقه پردازش نهایی می‌شوند.") #

        for index, row in df_final_positions.iterrows():
            row_skipped = False
            position_id_debug = "N/A" 
            try:
                position_id_debug = str(row.get('position_id', 'N/A')).strip() 
                
                # اطمینان از اینکه position_id یک عدد صحیح است
                if not str(position_id_debug).isdigit():
                    # print(f"DEBUG_SKIP: Position ID '{position_id_debug}' عددی نیست. سطر رد شد. (Index: {index})") #
                    row_skipped = True
                    continue

                position_id = str(int(float(position_id_debug))).strip() 
                
                if db_manager.check_duplicate_trade(position_id=position_id):
                    row_skipped = True
                    duplicate_count += 1
                    continue
                
                open_time_str = str(row.get('open_time_raw', '')).strip()
                try:
                    open_dt_obj = pd.to_datetime(open_time_str, errors='coerce')
                    # اصلاح: استفاده از pd.isna() به جای pd.isnat()
                    if pd.isna(open_dt_obj): 
                        raise ValueError(f"زمان باز شدن نامعتبر: '{open_time_str}'")
                        
                    open_dt_obj += timedelta(minutes=30) 

                    trade_date = open_dt_obj.strftime('%Y-%m-%d')
                    trade_time = open_dt_obj.strftime('%H:%M')
                except ValueError as ve:
                    # print(f"DEBUG_SKIP: خطای زمان باز شدن برای Position ID {position_id_debug}: {ve}. سطر رد شد. (Index: {index})") #
                    row_skipped = True
                    continue 
                
                symbol = str(row.get('symbol', '')).strip()
                trade_type = str(row.get('trade_type', '')).strip()

                # استخراج و اعتبارسنجی سایر فیلدهای عددی با Decimal
                size_raw_val = str(row.get('size_raw', '')).strip()
                size = _clean_numeric_value(size_raw_val)
                if size is None:
                    # print(f"DEBUG_SKIP: مقدار 'size' برای Position ID {position_id_debug} ('{size_raw_val}') قابل تبدیل به عدد نبود. سطر رد شد. (Index: {index})") #
                    row_skipped = True
                    continue
                
                entry_price_raw_val = str(row.get('entry_price_raw', '')).strip()
                entry_price = _clean_numeric_value(entry_price_raw_val)
                if entry_price is None:
                    # print(f"DEBUG_SKIP: مقدار 'entry_price' برای Position ID {position_id_debug} ('{entry_price_raw_val}') قابل تبدیل به عدد نبود. سطر رد شد. (Index: {index})") #
                    row_skipped = True
                    continue

                exit_price_raw_val = str(row.get('exit_price_raw', '')).strip()
                exit_price = _clean_numeric_value(exit_price_raw_val)
                if exit_price is None:
                    # print(f"DEBUG_SKIP: مقدار 'exit_price' برای Position ID {position_id_debug} ('{exit_price_raw_val}') قابل تبدیل به عدد نبود. سطر رد شد. (Index: {index})") #
                    row_skipped = True
                    continue

                profit_amount_raw_val = str(row.get('profit_amount_raw', '')).strip()
                profit_amount = _clean_numeric_value(profit_amount_raw_val)
                if profit_amount is None:
                    # print(f"DEBUG_SKIP: مقدار 'profit_amount' برای Position ID {position_id_debug} ('{profit_amount_raw_val}') قابل تبدیل به عدد نبود. سطر رد شد. (Index: {index})") #
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
                # print(f"DEBUG_SKIP: ستون '{ke}' برای Position ID {position_id_debug} در ردیف پیدا نشد. سطر رد شد. (Index: {index})") #
                row_skipped = True
                continue
            except Exception as e:
                # print(f"DEBUG_SKIP: خطای ناشناخته در پردازش سطر برای Position ID {position_id_debug}: {e}. سطر رد شد. (Index: {index})") #
                row_skipped = True
                continue
            finally:
                if row_skipped:
                    skipped_error_count += 1

        print(f"--- پایان پردازش ---") #
        return prepared_trades_list, total_trades_in_file, duplicate_count, skipped_error_count

    except FileNotFoundError:
        print(f"خطا: فایل '{file_path}' پیدا نشد. لطفاً مطمئن شوید فایل در مسیر صحیح قرار دارد.") #
        return [], 0, 0, 0
    except pd.errors.EmptyDataError:
        print(f"خطا: فایل '{file_path}' خالی است یا فرمت آن صحیح نیست.") #
        return [], 0, 0, 0
    except Exception as e:
        print(f"خطای بحرانی در حین خواندن یا پردازش فایل Excel/CSV: {e}") #
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
            trade_type=trade_data['trade_type']
        ):
            imported_count += 1
        else:
            pass
    return imported_count


if __name__ == "__main__":
    db_manager.migrate_database()
    
    test_file_path = "ReportHistory-303941.xlsx" # نام فایل اکسل
    if os.path.exists(test_file_path):
        print(f"در حال پردازش فایل تستی Excel/CSV: {test_file_path}") #
        prepared_trades, total, dup, err = process_mt5_report_for_preview(test_file_path)
        print(f"\n--- نتایج پیش‌نمایش از فایل ---") #
        print(f"کل تریدها در فایل (قبل از فیلتر): {total}") #
        print(f"تعداد تریدهای جدید آماده برای ورود: {len(prepared_trades)}") #
        print(f"تعداد تریدهای تکراری (قبلاً در دیتابیس): {dup}") #
        print(f"تعداد ردیف‌های رد شده (خطا/فیلتر): {err}") #
        
        if prepared_trades:
            print("\n--- 5 ترید اول آماده برای ورود: ---") #
            for i, trade in enumerate(prepared_trades[:5]):
                print(f"ترید {i+1}:") #
                for key, value in trade.items():
                    print(f"  {key}: {value}") #
                print("-" * 20) #
        else:
            print("هیچ تریدی برای وارد کردن پیدا نشد.") #

    else:
        print(f"فایل تستی با نام '{test_file_path}' پیدا نشد. لطفاً آن را در کنار اسکریپت قرار دهید یا مسیر درست را وارد کنید.") #