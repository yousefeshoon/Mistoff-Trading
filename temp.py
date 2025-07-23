# temp_check_db.py
import sys
import os

# این خطوط برای اطمینان از اینکه پایتون میتونه db_manager رو پیدا کنه لازمه
# فرض می‌کنیم db_manager.py در همان دایرکتوری یا در sys.path هست.
# اگر db_manager در یک پوشه خاص (مثلاً 'modules' یا 'utils') بود، باید آن مسیر را به sys.path اضافه کنید.
# مثال: sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'modules')))

import db_manager

def run_db_check():
    print("--- بررسی تریدهای دیتابیس ---")
    user_display_timezone = db_manager.get_default_timezone()
    print(f"منطقه زمانی نمایش: {user_display_timezone}")

    all_trades = db_manager.get_all_trades(user_display_timezone)

    if not all_trades:
        print("هیچ تریدی در دیتابیس یافت نشد.")
        return

    print(f"تعداد کل تریدها: {len(all_trades)}")
    print("\n--- جزئیات تریدها (ID, Date, Time, Symbol, Profit, Errors) ---")
    for trade in all_trades:
        # اینجا فقط فیلدهای کلیدی رو چاپ می‌کنیم تا خروجی خیلی شلوغ نشه
        print(f"ID: {trade.get('id')}, Date: {trade.get('date')}, Time: {trade.get('time')}, "
              f"Symbol: {trade.get('symbol')}, Profit: {trade.get('profit')}, "
              f"Errors: '{trade.get('errors')}'")

    print("\n--- بررسی خطاهای موجود در دیتابیس (error_list) ---")
    all_errors_in_db = db_manager.get_all_errors()
    if all_errors_in_db:
        print(f"خطاهای تعریف شده در دیتابیس: {all_errors_in_db}")
    else:
        print("هیچ خطایی در لیست خطاها تعریف نشده است.")

if __name__ == '__main__':
    run_db_check()