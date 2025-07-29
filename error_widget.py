# error_widget.py

import tkinter as tk
from tkinter import ttk
import db_manager
from collections import Counter
import sys
import version_info
import report_selection_window 
from datetime import datetime # <<< اضافه شده: برای دریافت روز جاری
from persian_chart_utils import process_persian_text_for_matplotlib # <<< اضافه شده: برای پردازش متن فارسی

# تابع اصلی که حالا یک پنجره والد (parent) می‌گیرد
def show_error_frequency_widget(parent_window=None, open_toplevel_windows_list=None):
    # این متغیرها را اینجا تعریف می‌کنیم تا در scope بیرونی load_and_display_errors باشند
    # و بتوان از nonlocal برای ارجوع به آن‌ها از داخل تابع استفاده کرد.
    tree_frame = None
    tree = None
    no_error_label = None
    
    # متغیر برای نگهداری حالت نمایش انتخاب شده
    # این متغیر باید بعد از تعریف root یا Toplevel ایجاد شود
    display_mode_var = None # ابتدا None قرار می‌دهیم

    # <<< اضافه شده: متغیر و نام برای فیلتر روز جاری
    filter_by_current_weekday_var = None
    current_weekday_name_persian = ""
    # >>>

    # این تابع رو تعریف می‌کنیم تا بشه از داخل دکمه Refresh و همچنین از اول بارگذاری صداش زد
    def load_and_display_errors(*args): # *args اضافه شد تا بتونه رویداد Combobox رو هم بگیره
        nonlocal tree, tree_frame, no_error_label
        
        # مطمئن می‌شویم display_mode_var تعریف شده است
        if display_mode_var is None:
            # این حالت نباید رخ دهد اگر کد به درستی اجرا شود
            print("Error: display_mode_var is not initialized.")
            return

        # پاک کردن محتویات قبلی Treeview قبل از بارگذاری مجدد
        if tree and tree_frame and tree_frame.winfo_exists():
            for item in tree.get_children():
                tree.delete(item)

        selected_mode = display_mode_var.get()
        
        # دریافت آستانه درصد فراوانی از دیتابیس (فقط برای حالاتی که نیاز است)
        frequency_threshold = db_manager.get_error_frequency_threshold()
        
        raw_errors_all_trades = []
        trade_ids_for_error_check = [] # برای نگهداری ID تریدهایی که باید خطاهاشون شمارش بشه

        # گام اول: اعمال فیلتر کمبوباکس (فراوانی اشتباهات در زیان‌ها/سودها/کلی)
        if selected_mode == "فراوانی اشتباهات در زیان‌ها":
            # get_trades_by_filters را با فیلتر profit='Loss' و بدون فیلتر تاریخ استفاده می‌کنیم
            filtered_trades = db_manager.get_trades_by_filters(filters={'trade_type': 'Loss'}) 
        elif selected_mode == "فراوانی اشتباهات در سودها":
            # get_trades_by_filters را با فیلتر profit='Profit' و بدون فیلتر تاریخ استفاده می‌کنیم
            filtered_trades = db_manager.get_trades_by_filters(filters={'trade_type': 'Profit'}) 
        elif selected_mode == "فراوانی کلی":
            # get_trades_by_filters را بدون فیلتر profit یا تاریخ استفاده می‌کنیم (همه تریدها)
            filtered_trades = db_manager.get_trades_by_filters(filters={'trade_type': 'همه انواع'}) # 'همه انواع' یعنی همه Profit, Loss, RF

        # گام دوم: اعمال فیلتر روز جاری هفته (اگر چک‌باکس تیک خورده باشد)
        final_filtered_trades = []
        if filter_by_current_weekday_var.get():
            current_weekday_python_index = datetime.now().weekday() # 0=Monday, ..., 6=Sunday
            for trade in filtered_trades:
                trade_date_str = trade['date'] # تاریخ ترید به فرم YYYY-MM-DD (UTC)
                # برای بررسی روز هفته، نیاز به یک datetime object از تاریخ ترید داریم
                try:
                    trade_datetime_obj = datetime.strptime(trade_date_str, '%Y-%m-%d')
                    if trade_datetime_obj.weekday() == current_weekday_python_index:
                        final_filtered_trades.append(trade)
                except ValueError:
                    # اگر فرمت تاریخ اشتباه بود، این ترید را نادیده می‌گیریم یا خطا چاپ می‌کنیم
                    print(f"Warning: Could not parse date {trade_date_str} for weekday filter.")
                    continue
        else:
            final_filtered_trades = filtered_trades

        raw_errors = [trade['errors'] for trade in final_filtered_trades]
        total_relevant_trades = len(final_filtered_trades)

        # شمارش خطاها
        error_counts = {}
        for error_string in raw_errors:
            if error_string:
                # استفاده از set برای شمارش هر خطا یک بار در هر ترید
                error_list_for_trade = [e.strip() for e in error_string.split(",")]
                for error in set(error_list_for_trade):
                    error_counts[error] = error_counts.get(error, 0) + 1

        # نمایش یا عدم نمایش Treeview بر اساس وجود خطا
        # و یا وجود ترید مرتبط برای محاسبه درصد
        if total_relevant_trades == 0 or not error_counts:
            if tree_frame and tree_frame.winfo_exists():
                tree_frame.destroy()
                tree = None
            if no_error_label is None or not no_error_label.winfo_exists():
                no_error_label = tk.Label(root, text=process_persian_text_for_matplotlib("هیچ خطایی برای نمایش در این حالت وجود ندارد."), anchor="center") # <<< فارسی‌سازی
                no_error_label.pack(pady=20)
            else:
                 no_error_label.config(text=process_persian_text_for_matplotlib("هیچ خطایی برای نمایش در این حالت وجود ندارد.")) # <<< فارسی‌سازی
        else:
            if tree_frame is None or not tree_frame.winfo_exists():
                tree_frame = tk.Frame(root)
                tree_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

                tree = ttk.Treeview(tree_frame, columns=("error", "percent"), show="headings", height=15)
                tree.heading("error", text=process_persian_text_for_matplotlib("نوع خطا")) # <<< فارسی‌سازی
                tree.heading("percent", text=process_persian_text_for_matplotlib("درصد فراوانی")) # <<< فارسی‌سازی
                tree.column("error", width=200, anchor="e")
                tree.column("percent", width=100, anchor="center")
                tree.pack(fill=tk.BOTH, expand=True)
                
                if no_error_label and no_error_label.winfo_exists():
                    no_error_label.destroy()
                    no_error_label = None

            # پر کردن Treeview با داده‌های جدید، با اعمال فیلتر درصد فراوانی (فقط در صورت نیاز)
            sorted_errors = sorted(error_counts.items(), key=lambda item: item[1], reverse=True)
            for error, freq in sorted_errors:
                percent = (freq / total_relevant_trades) * 100 
                
                if selected_mode == "فراوانی کلی" or percent >= float(frequency_threshold): 
                    tree.insert('', tk.END, values=(process_persian_text_for_matplotlib(error), f"{percent:.1f} %")) # <<< فارسی‌سازی

        # تنظیم خودکار Refresh (مثلاً هر 5 دقیقه یک بار) - فقط برای اجرای مستقل
        if not parent_window:
            root.after(300000, load_and_display_errors)

    # ایجاد پنجره Tkinter
    if parent_window:
        root = tk.Toplevel(parent_window)
    else:
        root = tk.Tk()
        root.attributes('-topmost', True)
        root.resizable(False, False)
        # توجه: اگر به صورت مستقل اجرا شود، مدیریت OPEN_TOPLEVEL_WINDOWS اینجا نیاز نیست.
        # فقط وقتی به عنوان Toplevel در برنامه اصلی باز می‌شود، باید به لیست اضافه شود.
    
    # اضافه کردن پنجره به لیست
    if open_toplevel_windows_list is not None:
        open_toplevel_windows_list.append(root) # <<< اضافه شده

    # تابع برای حذف پنجره از لیست هنگام بسته شدن
    def on_error_widget_close():
        if open_toplevel_windows_list is not None and root in open_toplevel_windows_list:
            open_toplevel_windows_list.remove(root) # <<< اضافه شده
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_error_widget_close) # <<< اضافه شده: هندل کردن دکمه بستن


    root.title(f" فراوانی خطاها - {version_info.__version__}")
    root.geometry("320x300")
    
    display_mode_var = tk.StringVar(root)
    display_mode_var.set("فراوانی اشتباهات در زیان‌ها") # حالت پیش‌فرض

    # Combobox برای انتخاب حالت نمایش
    mode_options = [process_persian_text_for_matplotlib("فراوانی اشتباهات در زیان‌ها"), # <<< فارسی‌سازی
                    process_persian_text_for_matplotlib("فراوانی اشتباهات در سودها"), # <<< فارسی‌سازی
                    process_persian_text_for_matplotlib("فراوانی کلی")] # <<< فارسی‌سازی
    mode_combobox = ttk.Combobox(root, textvariable=display_mode_var, values=mode_options, state="readonly", width=30)
    mode_combobox.pack(pady=10)
    mode_combobox.bind("<<ComboboxSelected>>", load_and_display_errors)

    # <<< اضافه شده: چک‌باکس فیلتر بر اساس روز جاری
    current_weekday_name_persian = ""
    weekday_names_persian_map = {
        0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنج‌شنبه", 4: "جمعه", 5: "شنبه", 6: "یکشنبه"
    }
    current_weekday_index = datetime.now().weekday()
    current_weekday_name_persian = weekday_names_persian_map.get(current_weekday_index, "نامشخص")
    
    filter_by_current_weekday_var = tk.BooleanVar(root)
    # در حالت پیشفرض، تیک نخورده است
    filter_by_current_weekday_var.set(False) 

    # عنوان چک باکس: فیلتر دوشنبه‌ها (اسم این گزینه از روز جاری برداشته میشه)
    checkbox_text = process_persian_text_for_matplotlib(f"فقط تریدهای {current_weekday_name_persian} ها")
    filter_weekday_chk = tk.Checkbutton(root, text=checkbox_text, variable=filter_by_current_weekday_var, command=load_and_display_errors)
    filter_weekday_chk.pack(pady=(0, 10))
    # >>>

    # فریم برای دکمه‌ها
    button_frame = tk.Frame(root)
    button_frame.pack(pady=5)

    # دکمه Refresh
    refresh_button = tk.Button(button_frame, text=process_persian_text_for_matplotlib("🔄 Refresh"), command=load_and_display_errors) # <<< فارسی‌سازی
    refresh_button.pack(side=tk.LEFT, padx=5)

    # <<< اضافه شده: دکمه گزارش جامع
    #tk.Button(button_frame, text=process_persian_text_for_matplotlib("📊 گزارش جامع"), # <<< فارسی‌سازی
    #         command=lambda: report_selection_window.ReportSelectionWindow(root, open_toplevel_windows_list), 
    #          bg="#A9DFBF", # رنگ پس زمینه متفاوت
    #          activebackground="#82CBB2" # رنگ هنگام کلیک
    #          ).pack(side=tk.LEFT, padx=5)
    # >>>

    # بارگذاری اولیه داده‌ها
    load_and_display_errors()

    # اگر مستقل اجرا شده، mainloop را صدا بزن
    if not parent_window:
        root.mainloop()

# تست اجرا
if __name__ == "__main__":
    db_manager.migrate_database()
    show_error_frequency_widget()