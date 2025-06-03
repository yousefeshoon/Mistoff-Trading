# error_widget.py

import tkinter as tk
from tkinter import ttk
import db_manager
from collections import Counter
import sys
import version_info

# تابع اصلی که حالا یک پنجره والد (parent) می‌گیرد
def show_error_frequency_widget(parent_window=None):
    # این متغیرها را اینجا تعریف می‌کنیم تا در scope بیرونی load_and_display_errors باشند
    # و بتوان از nonlocal برای ارجوع به آن‌ها از داخل تابع استفاده کرد.
    tree_frame = None
    tree = None
    no_error_label = None
    
    # متغیر برای نگهداری حالت نمایش انتخاب شده
    # این متغیر باید بعد از تعریف root یا Toplevel ایجاد شود
    display_mode_var = None # ابتدا None قرار می‌دهیم

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
        
        raw_errors = []
        total_relevant_trades = 0

        if selected_mode == "فراوانی اشتباهات در زیان‌ها":
            raw_errors = db_manager.get_loss_trades_errors()
            total_relevant_trades = db_manager.get_loss_trades_count()
        elif selected_mode == "فراوانی اشتباهات در سودها":
            raw_errors = db_manager.get_profit_trades_errors()
            total_relevant_trades = db_manager.get_profit_trades_count()
        elif selected_mode == "فراوانی کلی":
            raw_errors = db_manager.get_all_trades_errors()
            total_relevant_trades = db_manager.get_total_trades_count()
            # نکته: اگر total_relevant_trades صفر باشد اما raw_errors حاوی دیتا باشد،
            # این حالت به معنی وجود خطا در تریدهای "غیر زیان/سود" است.
            # در این صورت، برای جلوگیری از تقسیم بر صفر و نمایش صحیح،
            # می‌توانیم total_relevant_trades را حداقل 1 در نظر بگیریم
            # اگر هدف نمایش هر خطای موجود باشد.
            # اما منطقی‌تر این است که اگر تعداد تریدها صفر است، پیامی مبنی بر عدم وجود ترید بدهیم.
            # فعلاً رفتار موجود را حفظ می‌کنیم.

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
        if total_relevant_trades == 0 or not error_counts: # اگر هیچ ترید مرتبط یا خطایی وجود نداشته باشد
            if tree_frame and tree_frame.winfo_exists():
                tree_frame.destroy()
                tree = None
            if no_error_label is None or not no_error_label.winfo_exists():
                no_error_label = tk.Label(root, text="هیچ خطایی برای نمایش در این حالت وجود ندارد.", anchor="center")
                no_error_label.pack(pady=20)
            else:
                 no_error_label.config(text="هیچ خطایی برای نمایش در این حالت وجود ندارد.")
        else:
            if tree_frame is None or not tree_frame.winfo_exists():
                tree_frame = tk.Frame(root)
                tree_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

                tree = ttk.Treeview(tree_frame, columns=("error", "percent"), show="headings", height=15)
                tree.heading("error", text="نوع خطا")
                tree.heading("percent", text="درصد فراوانی")
                tree.column("error", width=200, anchor="e")
                tree.column("percent", width=100, anchor="center")
                tree.pack(fill=tk.BOTH, expand=True)
                
                if no_error_label and no_error_label.winfo_exists():
                    no_error_label.destroy()
                    no_error_label = None

            # پر کردن Treeview با داده‌های جدید، با اعمال فیلتر درصد فراوانی (فقط در صورت نیاز)
            sorted_errors = sorted(error_counts.items(), key=lambda item: item[1], reverse=True)
            for error, freq in sorted_errors:
                # اگر total_relevant_trades صفر باشد، درصد را به عنوان N/A نمایش می‌دهیم
                # یا می‌توانیم این مورد را در شرط بالا handle کنیم تا به اینجا نرسد.
                # فرض می‌کنیم total_relevant_trades > 0 در این بلوک.
                percent = (freq / total_relevant_trades) * 100 
                
                # اعمال فیلتر درصد فقط برای حالت‌های خاص
                # در حالت 'فراوانی کلی'، آستانه اعمال نمی‌شود
                if selected_mode == "فراوانی کلی" or percent >= float(frequency_threshold): #
                    tree.insert('', tk.END, values=(error, f"{percent:.1f} %"))

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
        root.bind('<Escape>', lambda e: root.destroy())
        root.protocol("WM_DELETE_WINDOW", root.destroy)

    root.title(f" فراوانی خطاها - {version_info.__version__}")
    root.geometry("320x400")
    
    # متغیر برای نگهداری حالت نمایش انتخاب شده
    # این متغیر باید بعد از تعریف root یا Toplevel ایجاد شود
    display_mode_var = tk.StringVar(root)
    display_mode_var.set("فراوانی اشتباهات در زیان‌ها") # حالت پیش‌فرض

    # Combobox برای انتخاب حالت نمایش
    mode_options = ["فراوانی اشتباهات در زیان‌ها", "فراوانی اشتباهات در سودها", "فراوانی کلی"]
    mode_combobox = ttk.Combobox(root, textvariable=display_mode_var, values=mode_options, state="readonly", width=30)
    mode_combobox.pack(pady=10)
    mode_combobox.bind("<<ComboboxSelected>>", load_and_display_errors)

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
    db_manager.migrate_database()
    show_error_frequency_widget()