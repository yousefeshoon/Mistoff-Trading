import tkinter as tk
from tkinter import ttk
import db_manager
from collections import Counter
import sys

# تابع اصلی که حالا یک پنجره والد (parent) می‌گیرد
def show_error_frequency_widget(parent_window=None):
    # این متغیرها را اینجا تعریف می‌کنیم تا در scope بیرونی load_and_display_errors باشند
    # و بتوان از nonlocal برای ارجاع به آن‌ها از داخل تابع استفاده کرد.
    tree_frame = None
    tree = None
    no_error_label = None # همچنین این لیبل را هم اینجا تعریف می‌کنیم
    info_label = None # این لیبل را هم اینجا تعریف می‌کنیم


    # این تابع رو تعریف می‌کنیم تا بشه از داخل دکمه Refresh و همچنین از اول بارگذاری صداش زد
    def load_and_display_errors():
        nonlocal tree, tree_frame, no_error_label, info_label # حالا اینجا اعلان می‌کنیم

        # پاک کردن محتویات قبلی Treeview قبل از بارگذاری مجدد
        # اگر tree_frame هنوز ایجاد نشده، این بخش را رد می‌کنیم
        if tree and tree_frame and tree_frame.winfo_exists():
            for item in tree.get_children():
                tree.delete(item)

        # از db_manager برای دریافت تعداد کل تریدها استفاده می‌کنیم
        total_trades = db_manager.get_total_trades_count()

        # از db_manager برای دریافت خطاهای تریدهای زیان‌ده استفاده می‌کنیم
        loss_trade_errors_raw = db_manager.get_loss_trades_errors()
        
        # شمارش خطاها در تریدهای زیان‌ده
        error_counts = {}
        for error_string in loss_trade_errors_raw:
            if error_string:
                error_list_for_trade = [e.strip() for e in error_string.split(",")]
                for error in set(error_list_for_trade):
                    error_counts[error] = error_counts.get(error, 0) + 1

        total_loss_trades = len(loss_trade_errors_raw)

        # به‌روزرسانی لیبل اطلاعات
        # اطمینان حاصل می‌کنیم که info_label قبل از config کردن ایجاد شده است
        if info_label:
            info_label.config(text=f"کل تریدها: {total_trades}     |     تریدهای زیان‌ده: {total_loss_trades}")

        # نمایش یا عدم نمایش Treeview بر اساس وجود خطا
        if total_loss_trades == 0:
            if tree_frame and tree_frame.winfo_exists(): # اگر Treeview قبلا وجود داشته، حذفش کن
                tree_frame.destroy()
                tree = None # tree را هم null می‌کنیم
            if no_error_label is None or not no_error_label.winfo_exists(): # اگر لیبل هنوز ساخته نشده بود
                no_error_label = tk.Label(root, text="هیچ خطایی ثبت نشده", anchor="center")
                no_error_label.pack(pady=20)
            else:
                 no_error_label.config(text="هیچ خطایی ثبت نشده") # اگر از قبل بود، فقط متنشو تغییر بده
            
        else:
            # اگر Treeview قبلا وجود نداشت، بسازش
            if tree_frame is None or not tree_frame.winfo_exists():
                tree_frame = tk.Frame(root)
                tree_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

                tree = ttk.Treeview(tree_frame, columns=("error", "percent"), show="headings", height=15)
                tree.heading("error", text="نوع خطا")
                tree.heading("percent", text="درصد فراوانی")
                tree.column("error", width=200, anchor="e")
                tree.column("percent", width=100, anchor="center")
                tree.pack(fill=tk.BOTH, expand=True)
                
                # حذف پیام "هیچ خطایی ثبت نشده" اگر وجود داشت
                if no_error_label and no_error_label.winfo_exists():
                    no_error_label.destroy()
                    no_error_label = None # null کردن بعد از destroy


            # پر کردن Treeview با داده‌های جدید
            sorted_errors = sorted(error_counts.items(), key=lambda item: item[1], reverse=True)
            for error, freq in sorted_errors:
                percent = (freq / total_loss_trades) * 100
                tree.insert('', tk.END, values=(error, f"{percent:.1f} %"))

        # تنظیم خودکار Refresh (مثلاً هر 5 دقیقه یک بار)
        if not parent_window:
            root.after(300000, load_and_display_errors) # 300000 میلی‌ثانیه = 5 دقیقه

    # ایجاد پنجره Tkinter
    if parent_window:
        root = tk.Toplevel(parent_window)
    else:
        root = tk.Tk()
        # فقط برای اجرای مستقل
        root.attributes('-topmost', True) 
        root.resizable(False, False)
        # برای بستن ویجت با فشردن Esc یا Ctrl+C
        root.bind('<Escape>', lambda e: root.destroy())
        root.protocol("WM_DELETE_WINDOW", root.destroy) # برای بستن عادی پنجره

        # اضافه کردن دکمه بستن برای ویجت مستقل
        close_btn = tk.Button(root, text="بستن ویجت", command=root.destroy)
        close_btn.pack(pady=5)

    root.title("درصد فراوانی خطاها")
    root.geometry("320x400")
    
    tk.Label(root, text="درصد فراوانی خطاها", font=("Segoe UI", 12, "bold"), anchor="center").pack(pady=10)

    # لیبل اطلاعات کلی
    # این لیبل باید قبل از فراخوانی load_and_display_errors ساخته شود
    info_label = tk.Label(root, text="", font=("Segoe UI", 10, "italic"))
    info_label.pack(pady=15)

    # دکمه Refresh
    refresh_button = tk.Button(root, text="🔄 Refresh", command=load_and_display_errors)
    refresh_button.pack(pady=5)

    # بارگذاری اولیه داده‌ها
    load_and_display_errors()

    # اگر مستقل اجرا شده، mainloop را صدا بزن
    if not parent_window:
        root.mainloop()

# تست اجرا
if __name__ == "__main__":
    db_manager.create_trades_table()
    show_error_frequency_widget()