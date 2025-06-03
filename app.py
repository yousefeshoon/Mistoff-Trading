import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
from tkcalendar import DateEntry
import os
import version_info
import sys
import pytz
from datetime import datetime
from decimal import Decimal, InvalidOperation

# ایمپورت ماژول mt5_importer
import mt5_importer

def get_resource_path(relative_path):
    """
    مسیر صحیح یک فایل را در محیط توسعه یا پس از کامپایل با PyInstaller برمی‌گرداند.
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ایمپورت کردن ماژول‌های خودت
import db_manager
from view_trades import show_trades_window
from error_widget import show_error_frequency_widget
from tkinter import simpledialog

db_manager.migrate_database()

APP_VERSION = version_info.__version__

root = tk.Tk()
root.iconbitmap(os.path.join(os.path.dirname(__file__), "icon.ico"))
root.title(f"MistOff Trading - {APP_VERSION}")
root.geometry("450x750")

# تعریف main_frame در اینجا، قبل از استفاده شدن
main_frame = tk.Frame(root)
main_frame.pack(padx=10, pady=10)

# >>> لیبل نمایش منطقه زمانی فعال
current_timezone_label = tk.Label(root, text="", fg="blue", font=("Segoe UI", 10, "bold"))
current_timezone_label.pack(pady=(0, 5))

def update_timezone_display():
    current_tz_name = db_manager.get_default_timezone()
    current_timezone_label.config(text=f"⏰ منطقه زمانی فعال: {current_tz_name}")

# <<<

def save_trade(event=None):
    date_str = entry_date.get()
    time_str = entry_time.get()
    symbol = entry_symbol.get()
    entry = entry_entry.get()
    exit_price = entry_exit.get()
    size = entry_size.get()
    profit = profit_var.get()
    
    trade_type = trade_type_var.get()

    selected_errors = [error for error, var in error_vars.items() if var.get()]
    
    if not time_str:
        messagebox.showerror("Missing Time", "لطفاً ساعت معامله را وارد کنید.")
        return

    # >>> تبدیل تاریخ و زمان ورودی دستی به UTC
    try:
        # دریافت تایم زون فعال کاربر برای ورودی دستی
        user_timezone_name = db_manager.get_default_timezone()
        user_tz = pytz.timezone(user_timezone_name)

        # ساخت datetime object naive از ورودی کاربر
        naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        
        # آگاه کردن datetime object به تایم زون کاربر
        aware_dt = user_tz.localize(naive_dt, is_dst=None)
        
        # تبدیل به UTC برای ذخیره در دیتابیس
        utc_dt = aware_dt.astimezone(pytz.utc)

        date_to_save = utc_dt.strftime('%Y-%m-%d')
        time_to_save = utc_dt.strftime('%H:%M')
    except ValueError as ve:
        messagebox.showerror("خطا در زمان", f"فرمت تاریخ یا زمان نامعتبر است: {ve}")
        return
    except Exception as e:
        messagebox.showerror("خطا", f"خطایی در تبدیل زمان رخ داد: {e}")
        return
    # <<<

    if db_manager.check_duplicate_trade(date_to_save, time_to_save):
        messagebox.showerror("Duplicate Entry", "تریدی با این تاریخ و ساعت (در منطقه زمانی UTC) قبلاً ثبت شده است")
        return
        
    if profit == "Loss" and not selected_errors:
        messagebox.showerror("Missing Error", "برای ترید ضررده، حداقل یک خطا باید انتخاب شود.")
        return

    # اعتبارسنجی ورودی‌های عددی قبل از ذخیره
    # از Decimal برای دقت بالاتر استفاده می‌کنیم
    try:
        entry_val = Decimal(entry) if entry else None
    except InvalidOperation:
        messagebox.showerror("خطا", "قیمت ورود نامعتبر است. لطفاً یک عدد وارد کنید.")
        return
    
    try:
        exit_val = Decimal(exit_price) if exit_price else None
    except InvalidOperation:
        messagebox.showerror("خطا", "قیمت خروج نامعتبر است. لطفاً یک عدد وارد کنید.")
        return
    
    try:
        size_val = Decimal(size) if size else Decimal('0.0')
    except InvalidOperation:
        messagebox.showerror("خطا", "سایز نامعتبر است. لطفاً یک عدد وارد کنید.")
        return
    
    # برای تریدهای دستی، actual_profit_amount نداریم، پس None میفرستیم
    actual_profit_amount_for_manual_trade = None

    if not db_manager.add_trade(date_to_save, time_to_save, symbol,
                                 entry_val,
                                 exit_val,
                                 profit,
                                 ', '.join(selected_errors),
                                 size_val,
                                 position_id=None,
                                 trade_type=trade_type,
                                 original_timezone_name=user_timezone_name,
                                 actual_profit_amount=actual_profit_amount_for_manual_trade):
        messagebox.showerror("خطا", "خطایی در ذخیره ترید رخ داد.")
        return
    
    for error in selected_errors:
        db_manager.add_error_to_list(error)

    messagebox.showinfo("Saved", "Trade saved successfully.")
    update_trade_count()
    
    profit_count, loss_count = count_trades_by_type()
    profit_label.config(text=f"تعداد تریدهای سودده: {profit_count}")
    loss_label.config(text=f"تعداد تریدهای زیان‌ده: {loss_count}")

    entry_time.delete(0, tk.END)
    entry_entry.delete(0, tk.END)
    entry_exit.delete(0, tk.END)
    profit_var.set("Profit")
    trade_type_var.set("buy")
    for var in error_vars.values():
        var.set(False)


def clear_fields():
    entry_date.set_date('')
    entry_time.delete(0, tk.END)
    entry_symbol.delete(0, tk.END)
    entry_symbol.insert(0, "US30")
    entry_entry.delete(0, tk.END)
    entry_exit.delete(0, tk.END)
    entry_size.delete(0, tk.END)
    profit_var.set("Profit")
    trade_type_var.set("buy")
    for var in error_vars.values():
        var.set(False)

def load_errors():
    return db_manager.get_all_errors()

def refresh_error_checkboxes():
    global error_names, error_vars
    for widget in error_frame.winfo_children():
        widget.destroy()
    error_names = load_errors()
    error_vars = {}
    for i, name in enumerate(error_names):
        var = tk.BooleanVar()
        chk = tk.Checkbutton(error_frame, text=name, variable=var, anchor='w', justify='left')
        chk.grid(row=i, column=0, sticky='w')
        error_vars[name] = var

def update_trade_count():
    count = db_manager.get_total_trades_count()
    trade_count_label.config(text=f"📈 تعداد تریدها: {count}")

def count_trades_by_type():
    profit_count = db_manager.get_profit_trades_count()
    loss_count = db_manager.get_loss_trades_count()
    return profit_count, loss_count

def add_labeled_entry(row, label_text, widget):
    label = tk.Label(main_frame, text=label_text, anchor='e', width=15)
    label.grid(row=row, column=0, padx=5, pady=5, sticky='e')
    widget.grid(row=row, column=1, padx=5, pady=5, sticky='w')

def edit_errors_window():
    window = tk.Toplevel(root)
    window.title("ویرایش خطاها")
    window.geometry("400x480")

    main_edit_frame = tk.Frame(window)
    main_edit_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    tree_section_frame = tk.Frame(main_edit_frame)
    tree_section_frame.pack(fill=tk.BOTH, expand=True)

    tree = ttk.Treeview(tree_section_frame, columns=("Error", "Count"), show="headings", height=15)
    tree.heading("Error", text="عنوان خطا")
    tree.heading("Count", text="تعداد استفاده")
    tree.pack(fill=tk.BOTH, expand=True)

    btn_frame = tk.Frame(main_edit_frame)
    btn_frame.pack(pady=5)

    add_error_section_frame = tk.Frame(main_edit_frame)
    add_error_section_frame.pack(pady=10)

    def refresh_edit_errors_treeview():
        for item in tree.get_children():
            tree.delete(item)
        
        errors_from_db = db_manager.get_all_errors_with_id()
        error_counts = db_manager.get_error_usage_counts()

        for eid, err_text in errors_from_db:
            count = error_counts.get(err_text, 0)
            tree.insert("", "end", iid=str(eid), values=(err_text, count))

    def delete_selected():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("هشدار", "هیچ خطایی انتخاب نشده است.")
            return
        
        eid = selected[0]
        err_text = tree.item(eid)["values"][0]
        count = tree.item(eid)["values"][1]

        if count > 0:
            messagebox.showwarning("خطا", "فقط خطاهایی که استفاده نشده‌اند قابل حذف هستند.")
            return
        
        if db_manager.delete_error_from_list(eid):
            tree.delete(eid)
            messagebox.showinfo("موفقیت", "خطا با موفقیت حذف شد.")
            refresh_error_checkboxes()
            refresh_edit_errors_treeview()
        else:
            messagebox.showerror("خطا", "خطایی در حذف خطا رخ داد.")

    def rename_selected():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("هشدار", "هیچ خطایی انتخاب نشده است.")
            return

        eid = selected[0]
        current_text = tree.item(eid)["values"][0]
        new_name = simpledialog.askstring("ویرایش عنوان", f"عنوان جدید برای «{current_text}» را وارد کنید:")

        if not new_name:
            return

        new_name = new_name.strip()
        if new_name == current_text:
            return

        result = db_manager.rename_error(eid, current_text, new_name)
        if result == "success":
            messagebox.showinfo("موفقیت", "عنوان خطا با موفقیت ویرایش شد.")
            tree.item(eid, values=(new_name, tree.item(eid)["values"][1]))
            refresh_error_checkboxes()
            refresh_edit_errors_treeview()
        elif result == "duplicate":
            messagebox.showerror("خطا", "این عنوان قبلاً وجود دارد.")
        else:
            messagebox.showerror("خطا", f"خطایی در ویرایش عنوان رخ داد: {str(result)}")
            
    def add_new_error_from_edit_window():
        new_error = new_error_entry.get().strip()
        if not new_error:
            messagebox.showwarning("هشدار", "عنوان خطا نمی‌تواند خالی باشد.")
            return
        
        result = db_manager.add_error_to_list(new_error)
        
        if result:
            messagebox.showinfo("موفقیت", "خطا با موفقیت اضافه شد.")
            refresh_edit_errors_treeview()
            refresh_error_checkboxes()
            new_error_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("هشدار", "این خطا قبلاً وجود دارد یا خطایی در ذخیره رخ داد.")

    tk.Button(btn_frame, text="🗑 حذف", command=delete_selected).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="✏️ تغییر عنوان", command=rename_selected).pack(side=tk.LEFT, padx=5)

    tk.Label(add_error_section_frame, text="", anchor='w').pack(side=tk.LEFT, padx=5)
    new_error_entry = tk.Entry(add_error_section_frame, width=30)
    new_error_entry.pack(side=tk.LEFT, padx=5)
    tk.Button(add_error_section_frame, text="➕ اضافه کردن", command=add_new_error_from_edit_window).pack(side=tk.LEFT, padx=5)

    refresh_edit_errors_treeview()

def select_report_file():
    file_path = filedialog.askopenfilename(
        title="انتخاب فایل گزارش اکسل متاتریدر 5",
        filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
    )
    if file_path:
        report_file_path_var.set(file_path)
    else:
        report_file_path_var.set("")
        messagebox.showwarning("انتخاب فایل", "انتخاب فایل گزارش اکسل لغو شد.")

def import_trades_from_report():
    file_path = report_file_path_var.get()
    if not file_path:
        messagebox.showwarning("خطا", "لطفاً ابتدا یک فایل گزارش را انتخاب کنید.")
        return
    
    if not os.path.exists(file_path):
        messagebox.showerror("خطا", f"فایل '{file_path}' یافت نشد.")
        report_file_path_var.set("")
        return

    try:
        prepared_trades_list, total_in_file, duplicate_count, error_count = \
            mt5_importer.process_mt5_report_for_preview(file_path)

        msg = (f"گزارش آماده وارد کردن:\n"
               f"تعداد کل تریدها در فایل: {total_in_file}\n"
               f"تعداد تریدهای جدید قابل وارد کردن: {len(prepared_trades_list)}\n"
               f"تعداد تریدهای تکراری (قبلاً در دیتابیس): {duplicate_count}\n"
               f"تعداد ردیف‌های رد شده (غیرمعتبر/فیلتر شده): {error_count}\n\n"
               f"آیا مطمئن هستید که می‌خواهید تریدهای جدید را وارد دیتابیس کنید؟")
        
        confirm_import = messagebox.askyesno("تأیید وارد کردن اطلاعات", msg)
        
        if confirm_import:
            actually_imported_count = mt5_importer.add_prepared_trades_to_db(prepared_trades_list)
            
            messagebox.showinfo("وارد کردن موفق", f"{actually_imported_count} ترید جدید با موفقیت وارد دیتابیس شد.")
            update_trade_count()
            profit_count, loss_count = count_trades_by_type()
            profit_label.config(text=f"تعداد تریدهای سودده: {profit_count}")
            loss_label.config(text=f"تعداد تریدهای زیان‌ده: {loss_count}")
        else:
            messagebox.showinfo("لغو", "وارد کردن اطلاعات لغو شد.")

    except Exception as e:
        messagebox.showerror("خطا در وارد کردن", f"خطایی در حین پردازش فایل رخ داد: {e}")
        print(f"Detailed import error: {e}")


def show_timezone_settings_window():
    settings_win = tk.Toplevel(root)
    settings_win.title("تنظیمات منطقه زمانی")
    settings_win.geometry("350x200")
    settings_win.transient(root)
    settings_win.grab_set()
    settings_win.resizable(False, False)

    root_width = root.winfo_width()
    root_height = root.winfo_height()
    settings_win_width = 350
    settings_win_height = 100
    x = root.winfo_x() + (root_width / 2) - (settings_win_width / 2)
    y = root.winfo_y() + (root_height / 2) - (settings_win_height / 2)
    settings_win.geometry(f'{settings_win_width}x{settings_win_height}+{int(x)}+{int(y)}')

    frame = tk.Frame(settings_win, padx=15, pady=15)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(frame, text="انتخاب منطقه زمانی پیش‌فرض:").grid(row=0, column=0, sticky="w", pady=5, padx=5)

    common_timezones = [
        'Asia/Tehran',
        'UTC',
        'Europe/London',
        'America/New_York',
        'America/Los_Angeles',
        'Asia/Dubai',
        'Asia/Tokyo',
        'Australia/Sydney',
        'Etc/GMT-3'
    ]
    current_tz = db_manager.get_default_timezone()
    
    tz_var = tk.StringVar(value=current_tz if current_tz in common_timezones else 'Asia/Tehran')
    tz_dropdown = ttk.Combobox(frame, textvariable=tz_var, values=common_timezones, state="readonly", width=20)
    tz_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    def save_settings():
        new_tz = tz_var.get()
        if db_manager.set_default_timezone(new_tz):
            messagebox.showinfo("موفقیت", "منطقه زمانی با موفقیت ذخیره شد.")
            update_timezone_display()
            settings_win.destroy()
        else:
            messagebox.showerror("خطا", "خطایی در ذخیره منطقه زمانی رخ داد.")

    btn_frame_settings = tk.Frame(frame)
    btn_frame_settings.grid(row=2, column=0, columnspan=2, pady=10)

    tk.Button(btn_frame_settings, text="ذخیره", command=save_settings).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame_settings, text="لغو", command=settings_win.destroy).pack(side=tk.LEFT, padx=5)

    settings_win.focus_set()
    settings_win.wait_window(settings_win)

def show_rf_threshold_settings_window():
    rf_win = tk.Toplevel(root)
    rf_win.title("تنظیم آستانه ریسک فری")
    rf_win.transient(root)
    rf_win.grab_set()
    rf_win.resizable(False, False)

    root_width = root.winfo_width()
    root_height = root.winfo_height()
    rf_win_width = 350
    rf_win_height = 150
    x = root.winfo_x() + (root_width / 2) - (rf_win_width / 2)
    y = root.winfo_y() + (root_height / 2) - (rf_win_height / 2)
    rf_win.geometry(f'{rf_win_width}x{rf_win_height}+{int(x)}+{int(y)}')

    frame = tk.Frame(rf_win, padx=15, pady=15)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(frame, text="مقدار آستانه برای ترید RF (مثلاً 1.5):").grid(row=0, column=0, sticky="w", pady=5, padx=5)
    tk.Label(frame, text="اگر سود/ضرر بین ±این مقدار باشد، RF در نظر گرفته می‌شود.", font=("Segoe UI", 8)).grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 10))

    current_rf_threshold = db_manager.get_rf_threshold()
    rf_threshold_var = tk.StringVar(value=str(current_rf_threshold))
    rf_entry = tk.Entry(frame, textvariable=rf_threshold_var, width=10)
    rf_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    def save_rf_settings():
        new_threshold_str = rf_threshold_var.get().strip()
        try:
            new_threshold = Decimal(new_threshold_str)
            if new_threshold < 0:
                messagebox.showwarning("خطا", "آستانه ریسک فری نمی‌تواند منفی باشد.")
                return
            
            if db_manager.set_rf_threshold(new_threshold):
                messagebox.showinfo("موفقیت", "آستانه ریسک فری با موفقیت ذخیره شد.")
                # >>> فراخوانی تابع بازبینی و آپدیت تریدها
                updated_count = db_manager.recalculate_trade_profits()
                if updated_count > 0:
                    messagebox.showinfo("بروزرسانی تریدها", f"{updated_count} ترید بر اساس آستانه جدید ریسک فری بروزرسانی شد.")
                else:
                    messagebox.showinfo("بروزرسانی تریدها", "هیچ تریدی نیاز به بروزرسانی بر اساس آستانه جدید ریسک فری نداشت.")
                update_trade_count()
                profit_count, loss_count = count_trades_by_type()
                profit_label.config(text=f"تعداد تریدهای سودده: {profit_count}")
                loss_label.config(text=f"تعداد تریدهای زیان‌ده: {loss_count}")
                # <<<
                rf_win.destroy()
            else:
                messagebox.showerror("خطا", "خطایی در ذخیره آستانه ریسک فری رخ داد.")
        except InvalidOperation:
            messagebox.showerror("خطا", "لطفاً یک عدد معتبر برای آستانه ریسک فری وارد کنید.")

    btn_frame_rf_settings = tk.Frame(frame)
    btn_frame_rf_settings.grid(row=3, column=0, columnspan=2, pady=10)

    tk.Button(btn_frame_rf_settings, text="ذخیره", command=save_rf_settings).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame_rf_settings, text="لغو", command=rf_win.destroy).pack(side=tk.LEFT, padx=5)

    rf_win.focus_set()
    rf_win.wait_window(rf_win)


def show_error_frequency_settings_window():
    freq_win = tk.Toplevel(root)
    freq_win.title("تنظیم آستانه درصد فراوانی خطا")
    freq_win.transient(root)
    freq_win.grab_set()
    freq_win.resizable(False, False)

    root_width = root.winfo_width()
    root_height = root.winfo_height()
    freq_win_width = 400
    freq_win_height = 150
    x = root.winfo_x() + (root_width / 2) - (freq_win_width / 2)
    y = root.winfo_y() + (root_height / 2) - (freq_win_height / 2)
    freq_win.geometry(f'{freq_win_width}x{freq_win_height}+{int(x)}+{int(y)}')

    frame = tk.Frame(freq_win, padx=15, pady=15)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(frame, text="خطاهای با درصد فراوانی کمتر از این مقدار،\nدر ویجت نمایش داده نمی‌شوند:").grid(row=0, column=0, sticky="w", pady=5, padx=5)
    #tk.Label(frame, text="(مثلاً 10 برای نمایش خطاهای با درصد بالای 10%)", font=("Segoe UI", 8, "italic")).grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 10))

    current_freq_threshold = db_manager.get_error_frequency_threshold()
    freq_threshold_var = tk.StringVar(value=str(current_freq_threshold))
    freq_entry = tk.Entry(frame, textvariable=freq_threshold_var, width=10)
    freq_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    def save_freq_settings():
        new_threshold_str = freq_threshold_var.get().strip()
        try:
            new_threshold = Decimal(new_threshold_str)
            if new_threshold < 0:
                messagebox.showwarning("خطا", "آستانه درصد فراوانی نمی‌تواند منفی باشد.")
                return
            
            if db_manager.set_error_frequency_threshold(new_threshold):
                messagebox.showinfo("موفقیت", "آستانه درصد فراوانی با موفقیت ذخیره شد.")
                freq_win.destroy()
            else:
                messagebox.showerror("خطا", "خطایی در ذخیره آستانه درصد فراوانی رخ داد.")
        except InvalidOperation:
            messagebox.showerror("خطا", "لطفاً یک عدد معتبر برای آستانه درصد فراوانی وارد کنید.")

    btn_frame_freq_settings = tk.Frame(frame)
    btn_frame_freq_settings.grid(row=3, column=0, columnspan=2, pady=10)

    tk.Button(btn_frame_freq_settings, text="ذخیره", command=save_freq_settings).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame_freq_settings, text="لغو", command=freq_win.destroy).pack(side=tk.LEFT, padx=5)

    freq_win.focus_set()
    freq_win.wait_window(freq_win)


# --- ویجت‌های فرم اصلی ---

# تاریخ
entry_date = DateEntry(main_frame, width=30, date_pattern='yyyy-mm-dd')
add_labeled_entry(0, "Date:", entry_date)

# ساعت (اختیاری)
entry_time = tk.Entry(main_frame, width=30)
add_labeled_entry(1, "Time:", entry_time)

# نماد
entry_symbol = tk.Entry(main_frame, width=30)
entry_symbol.insert(0, "US30")
add_labeled_entry(2, "Symbol:", entry_symbol)

# Trade Type (Radiobutton)
trade_type_var = tk.StringVar(value="buy")
trade_type_frame = tk.Frame(main_frame)
add_labeled_entry(3, "Trade Type:", trade_type_frame)

buy_radio = tk.Radiobutton(trade_type_frame, text="Buy", variable=trade_type_var, value="buy")
buy_radio.pack(side=tk.LEFT, padx=5)

sell_radio = tk.Radiobutton(trade_type_frame, text="Sell", variable=trade_type_var, value="sell")
sell_radio.pack(side=tk.LEFT, padx=5)

# قیمت ورود
entry_entry = tk.Entry(main_frame, width=30)
add_labeled_entry(4, "Entry (optional):", entry_entry)

# قیمت خروج
entry_exit = tk.Entry(main_frame, width=30)
add_labeled_entry(5, "Exit (optional):", entry_exit)

# Size
entry_size = tk.Entry(main_frame, width=30)
add_labeled_entry(6, "Size (optional):", entry_size)

# سود/ضرر/RF
profit_var = tk.StringVar()
profit_dropdown = ttk.Combobox(main_frame, textvariable=profit_var, values=["Profit", "Loss", "RF"], width=27)
profit_dropdown.current(0)
add_labeled_entry(7, "Profit / RF / Loss:", profit_dropdown)

# لیست چک‌باکس ایرادات
tk.Label(main_frame, text="Select Errors:", anchor='w').grid(row=8, column=0, sticky='ne', padx=5, pady=(10, 0))
error_frame = tk.Frame(main_frame)
error_frame.grid(row=8, column=1, columnspan=2, sticky='w', pady=(10, 0))
error_names = []
error_vars = {}
refresh_error_checkboxes()

# دکمه ذخیره
btn_save = tk.Button(main_frame, text="Save Trade", command=save_trade, width=20)
btn_save.grid(row=9, column=0, columnspan=3, pady=20)


# --- بخش جدید برای وارد کردن فایل Excel ---
report_import_frame = tk.LabelFrame(root, text="وارد کردن از گزارش MT5 (اکسل)")
report_import_frame.pack(padx=10, pady=10, fill=tk.X)

report_file_path_var = tk.StringVar()

tk.Label(report_import_frame, text="فایل گزارش اکسل:", anchor='w').grid(row=0, column=0, padx=5, pady=5, sticky='w')

report_path_entry = tk.Entry(report_import_frame, textvariable=report_file_path_var, width=40, state='readonly')
report_path_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

select_file_btn = tk.Button(report_import_frame, text="انتخاب فایل...", command=select_report_file)
select_file_btn.grid(row=0, column=2, padx=5, pady=5)

import_report_btn = tk.Button(report_import_frame, text="وارد کردن از گزارش", command=import_trades_from_report)
import_report_btn.grid(row=1, column=0, columnspan=3, pady=5)


# فریم افقی برای دکمه‌های اصلی (نمایش تریدها و فراوانی خطاها)
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

# دکمه نمایش تریدها (با ارسال کال‌بک‌ها)
tk.Button(button_frame, text="📄 نمایش تریدها",
          command=lambda: show_trades_window(root,
                                            refresh_main_errors_callback=refresh_error_checkboxes,
                                            update_main_timezone_display=update_timezone_display)).pack(side=tk.LEFT, padx=5)

# دکمه نمایش درصد فراوانی خطاها
tk.Button(button_frame, text="📊 فراوانی خطاها", command=lambda: show_error_frequency_widget(root)).pack(side=tk.LEFT, padx=5)

# دکمه ویرایش خطاها
tk.Button(button_frame, text="✏️ ویرایش خطاها", command=edit_errors_window).pack(side=tk.LEFT, padx=5)

# نمایش تعداد تریدهای سودده و زیان‌ده
profit_count, loss_count = count_trades_by_type()

frame_counts = tk.Frame(root)
frame_counts.pack(pady=(5, 10))

profit_label = tk.Label(frame_counts, text=f"تعداد تریدهای سودده: {profit_count}", fg="green")
profit_label.pack(side="left", padx=10)

loss_label = tk.Label(frame_counts, text=f"تعداد تریدهای زیان‌ده: {loss_count}", fg="red")
loss_label.pack(side="left", padx=10)

# Ctrl+S
root.bind('<Control-s>', save_trade)

# تعداد تریدها
trade_count_label = tk.Label(root, text="📈 تعداد کل تریدها: 0")
trade_count_label.pack(pady=5)
update_trade_count()

# پیام هشدار برای تریدهای تکراری در پایین فرم
warning_message_text = "کاربر گرامی، ورود تریدها بصورت دستی راحت تر بوده و الزامات کمتری دارد اما در صورتیکه بعدا فایل وارد کنید، تریدهای تکراری توسط نرم افزار قابل تشخیص نیست. لذا باید آنها بصورت دستی حذف شوند"
warning_label = tk.Label(root, text=warning_message_text, fg="gray", font=("Segoe UI", 9), wraplength=430, justify="center")
warning_label.pack(side=tk.BOTTOM, pady=(0, 5))

# >>> اضافه کردن منوی تنظیمات
menubar = tk.Menu(root)
root.config(menu=menubar)

settings_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="تنظیمات", menu=settings_menu)
settings_menu.add_command(label="تنظیم منطقه زمانی...", command=show_timezone_settings_window)
settings_menu.add_command(label="تعیین آستانه ریسک فری...", command=show_rf_threshold_settings_window)
settings_menu.add_command(label="تنظیم آستانه نمایش فراوانی خطاها...", command=show_error_frequency_settings_window)
# <<<

update_timezone_display()
root.mainloop()