# app.py

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

# ایمپورت ماژول‌های خودت
import db_manager
import mt5_importer
from view_trades import show_trades_window
from error_widget import show_error_frequency_widget
from tkinter import simpledialog
import settings_manager 
import report_selection_window 
import customtkinter as ctk 

db_manager.migrate_database()

APP_VERSION = version_info.__version__

root = tk.Tk()
root.iconbitmap(os.path.join(os.path.dirname(__file__), "icon.ico"))
root.title(f"MistOff Trading - {APP_VERSION}")

# --- لیست گلوبال برای نگهداری ارجاع به پنجره‌های Toplevel باز ---
# هر بار که یک پنجره Toplevel جدید باز می‌شود، باید به این لیست اضافه شود.
# هر بار که بسته می‌شود (با destroy)، باید از لیست حذف شود.
OPEN_TOPLEVEL_WINDOWS = []
# -------------------------------------------------------------

# محاسبه ابعاد صفحه نمایش
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# ابعاد فرم اصلی
main_form_width = 450
main_form_height = 750

# محاسبه موقعیت: 5% از بالا و سمت چپ (با یک فاصله مشخص)
x_position = 50 
y_position = int(screen_height * 0.05) 

root.geometry(f'{main_form_width}x{main_form_height}+{int(x_position)}+{int(y_position)}')

main_frame = tk.Frame(root)
main_frame.pack(padx=10, pady=10)

current_timezone_label = tk.Label(root, text="", fg="blue", font=("Vazirmatn", 10, "bold"))
current_timezone_label.pack(pady=(0, 5))

# تابع کال‌بک برای به‌روزرسانی نمایش منطقه زمانی (از settings_manager فراخوانی می‌شود)
def update_main_timezone_display_callback():
    settings_manager.update_timezone_display_for_main_app(current_timezone_label)

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

    try:
        user_timezone_name = db_manager.get_default_timezone()
        user_tz = pytz.timezone(user_timezone_name)

        naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        
        aware_dt = user_tz.localize(naive_dt, is_dst=None)
        
        utc_dt = aware_dt.astimezone(pytz.utc)

        date_to_save = utc_dt.strftime('%Y-%m-%d')
        time_to_save = utc_dt.strftime('%H:%M')
    except ValueError as ve:
        messagebox.showerror("خطا در زمان", f"فرمت تاریخ یا زمان نامعتبر است: {ve}")
        return
    except Exception as e:
        messagebox.showerror("خطا", f"خطایی در تبدیل زمان رخ داد: {e}")
        return

    if db_manager.check_duplicate_trade(date_to_save, time_to_save):
        messagebox.showerror("Duplicate Entry", "تریدی با این تاریخ و ساعت (در منطقه زمانی UTC) قبلاً ثبت شده است")
        return
        
    if profit == "Loss" and not selected_errors:
        messagebox.showerror("Missing Error", "برای ترید ضررده، حداقل یک خطا باید انتخاب شود.")
        return

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
    global error_names, error_vars, inner_error_frame, error_canvas, error_scrollbar
    
    # پاک کردن محتوای قبلی inner_error_frame
    for widget in inner_error_frame.winfo_children():
        widget.destroy()

    error_names = load_errors()
    error_vars = {}
    for i, name in enumerate(error_names):
        var = tk.BooleanVar()
        chk = tk.Checkbutton(inner_error_frame, text=name, variable=var, anchor='w', justify='left', background='white')
        chk.grid(row=i, column=0, sticky='w')
        error_vars[name] = var
    
    # به‌روزرسانی Scroll Region پس از اضافه شدن همه چک‌باکس‌ها
    inner_error_frame.update_idletasks() # اطمینان از به‌روزرسانی اندازه‌های ویجت‌ها
    error_canvas.config(scrollregion=error_canvas.bbox("all"))

    # نمایش یا پنهان کردن اسکرول‌بار بر اساس تعداد آیتم‌ها
    # فرض می‌کنیم ارتفاع هر چک‌باکس حدود 20-25 پیکسل است
    # ارتفاع 4 ردیف حدود 100 پیکسل (4 * 25)
    if len(error_names) > 4:
        error_canvas.config(height=100) # ارتفاع ثابت برای نمایش 4 آیتم
        error_scrollbar.pack(side="right", fill="y", padx=(0,0))
    else:
        error_canvas.config(height=25 * len(error_names) if len(error_names) > 0 else 1) # ارتفاع متناسب با تعداد آیتم‌ها
        error_scrollbar.pack_forget()


def update_trade_count():
    count = db_manager.get_total_trades_count()
    trade_count_label.config(text=f"📈 تعداد تریدها: {count}")

def add_labeled_entry(row, label_text, widget):
    label = tk.Label(main_frame, text=label_text, anchor='e', width=15)
    label.grid(row=row, column=0, padx=5, pady=5, sticky='e')
    widget.grid(row=row, column=1, padx=5, pady=5, sticky='w')

# تابع اصلی ویرایش خطاها، حالا آرگومان open_toplevel_windows_list را می‌پذیرد
def edit_errors_window(open_toplevel_windows_list=None): # <<< آرگومان جدید
    window = tk.Toplevel(root)
    # اضافه کردن پنجره به لیست
    if open_toplevel_windows_list is not None:
        open_toplevel_windows_list.append(window) # <<< اضافه شده
    
    window.title("ویرایش خطاها")
    window.geometry("400x480")

    # --- تنظیمات ttk.Style برای پنجره ویرایش خطاها ---
    # این کد تضمین می‌کند که استایل ttk برای این پنجره به درستی تنظیم شود
    # و تحت تأثیر تغییرات style در پنجره‌های customtkinter قرار نگیرد.
    style = ttk.Style()
    style.theme_use("clam") # یا هر تم دیگری که با Tkinter استاندارد خوب کار کند
    
    # تنظیمات عمومی برای دکمه‌ها
    style.configure("TButton",
                    font=("Vazirmatn", 10),
                    background="#E0E0E0", # رنگ پیش‌فرض دکمه
                    foreground="black",
                    padding=5)
    style.map("TButton",
              background=[('active', '#C0C0C0')],
              foreground=[('active', 'black')])

    # تنظیمات Treeview در پنجره ویرایش خطاها (اگه اینجا هم Treeview داری)
    style.configure("Treeview",
                    background="white",
                    foreground="black",
                    fieldbackground="white",
                    rowheight=25, # ارتفاع ردیف‌ها را کمی کمتر کن
                    borderwidth=1,
                    highlightthickness=0,
                    font=("Vazirmatn", 10))
    style.map('Treeview',
              background=[('selected', '#3B8ED0')],
              foreground=[('selected', 'white')])
    style.configure("Treeview.Heading",
                    font=("Vazirmatn", 10, "bold"),
                    background="#F0F0F0",
                    foreground="black",
                    padding=[5, 2],
                    relief="raised")
    style.map("Treeview.Heading",
              background=[('active', '#D0D0D0')])
    # --- پایان تنظیمات ttk.Style ---

    # تابع برای حذف پنجره از لیست هنگام بسته شدن
    def on_edit_errors_close():
        if open_toplevel_windows_list is not None and window in open_toplevel_windows_list:
            open_toplevel_windows_list.remove(window) # <<< اضافه شده
        window.destroy()

    window.protocol("WM_DELETE_WINDOW", on_edit_errors_close) # <<< اضافه شده: هندل کردن دکمه بستن


    main_edit_frame = tk.Frame(window)
    main_edit_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    tree_section_frame = tk.Frame(main_edit_frame)
    tree_section_frame.pack(fill=tk.BOTH, expand=True)

    tree = ttk.Treeview(tree_section_frame, columns=("Error", "Count"), show="headings", height=15)
    tree.heading("Error", text="عنوان خطا")
    tree.heading("Count", text="تعداد استفاده")
    tree.pack(fill=tk.BOTH, expand=True) # <<< مطمئن شو expand=True هست

    btn_frame = tk.Frame(main_edit_frame)
    btn_frame.pack(pady=5) # <<< این فریم رو pack می‌کنیم

    add_error_section_frame = tk.Frame(main_edit_frame)
    add_error_section_frame.pack(pady=10) # <<< این فریم رو pack می‌کنیم

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

    # استفاده از ttk.Button برای دکمه‌ها
    ttk.Button(btn_frame, text="🗑 حذف", command=delete_selected).pack(side=tk.LEFT, padx=5) # <<< تغییر به ttk.Button
    ttk.Button(btn_frame, text="✏️ تغییر عنوان", command=rename_selected).pack(side=tk.LEFT, padx=5) # <<< تغییر به ttk.Button

    tk.Label(add_error_section_frame, text="", anchor='w').pack(side=tk.LEFT, padx=5)
    new_error_entry = tk.Entry(add_error_section_frame, width=30)
    new_error_entry.pack(side=tk.LEFT, padx=5)
    ttk.Button(add_error_section_frame, text="➕ اضافه کردن", command=add_new_error_from_edit_window).pack(side=tk.LEFT, padx=5) # <<< تغییر به ttk.Button

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
        else:
            messagebox.showinfo("لغو", "وارد کردن اطلاعات لغو شد.")

    except Exception as e:
        messagebox.showerror("خطا در وارد کردن", f"خطایی در حین پردازش فایل رخ داد: {e}")
        print(f"Detailed import error: {e}")


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

# لیست چک‌باکس ایرادات (با Scrollbar)
tk.Label(main_frame, text="Select Errors:", anchor='w').grid(row=8, column=0, sticky='ne', padx=5, pady=(10, 0))

# فریم اصلی برای نگه داشتن Canvas و Scrollbar
error_scroll_frame = tk.Frame(main_frame)
error_scroll_frame.grid(row=8, column=1, columnspan=2, sticky='w', pady=(10, 0))

# Canvas برای اسکرول‌بار
error_canvas = tk.Canvas(error_scroll_frame, borderwidth=0, background="#ffffff", highlightthickness=0, width=220) 
error_canvas.pack(side="left", fill="y", expand=False)

# Scrollbar عمودی
error_scrollbar = ttk.Scrollbar(error_scroll_frame, orient="vertical", command=error_canvas.yview)
# هنوز پک نمی‌کنیم، فقط زمانی که نیاز شد پک می‌شود

# فریم داخلی که چک‌باکس‌ها را نگه می‌دارد و داخل Canvas قرار می‌گیرد
inner_error_frame = tk.Frame(error_canvas, background="#ffffff")
error_canvas.create_window((0, 0), window=inner_error_frame, anchor="nw")

# تنظیم اسکرول‌بار برای Canvas
error_canvas.configure(yscrollcommand=error_scrollbar.set)

# بایند کردن رویداد Configure به inner_error_frame برای به‌روزرسانی scrollregion
inner_error_frame.bind("<Configure>", lambda e: error_canvas.configure(scrollregion=error_canvas.bbox("all")))


error_names = []
error_vars = {}
refresh_error_checkboxes() # فراخوانی اولیه برای پر کردن چک‌باکس‌ها

# دکمه ذخیره
btn_save = tk.Button(main_frame, text="Save Trade", command=save_trade, width=20)
btn_save.grid(row=9, column=0, columnspan=3, pady=20)


# --- بخش جدید برای وارد کردن فایل Excel ---
report_import_frame = tk.LabelFrame(root, text="وارد کردن از گزارش متاتریدر (اکسل)")
report_import_frame.pack(padx=10, pady=10, fill=tk.X)

report_file_path_var = tk.StringVar()

tk.Label(report_import_frame, text="فایل گزارش اکسل:", anchor='w').grid(row=0, column=0, padx=5, pady=5, sticky='w')

report_path_entry = tk.Entry(report_import_frame, textvariable=report_file_path_var, width=35, state='readonly')
report_path_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

select_file_btn = tk.Button(report_import_frame, text="انتخاب فایل...", command=select_report_file)
select_file_btn.grid(row=0, column=2, padx=5, pady=5)

import_report_btn = tk.Button(report_import_frame, text="وارد کردن از گزارش", command=import_trades_from_report)
import_report_btn.grid(row=1, column=0, columnspan=3, pady=5)

# ابعاد اصلی فرم را در متغیرهای سراسری ذخیره می‌کنیم
ORIGINAL_MAIN_FORM_WIDTH = main_form_width
ORIGINAL_MAIN_FORM_HEIGHT = main_form_height
ORIGINAL_X_POSITION = x_position
ORIGINAL_Y_POSITION = y_position

# --- این تابع رو به بالا منتقل می‌کنیم تا قبل از استفاده ازش تعریف شده باشه ---
def show_report_selection_window_and_restore_main():
    # لیست پنجره‌های مینیمایز شده برای بازیابی
    minimized_windows = [] 

    # 1. پنجره اصلی (root) را قبل از هر چیز مینیمایز می‌کنیم
    if root.winfo_exists() and root.state() == 'normal':
        root.wm_state('iconic')
        minimized_windows.append(root)

    # 2. سایر پنجره‌های Toplevel باز شده را مینیمایز می‌کنیم
    # یک کپی از لیست می‌گیریم تا حین iterate کردن لیست اصلی تغییر نکنه
    for window in list(OPEN_TOPLEVEL_WINDOWS):
        if window.winfo_exists() and window.state() == 'normal':
            window.wm_state('iconic')
            minimized_windows.append(window)

    # 3. ReportSelectionWindow را ایجاد می‌کنیم.
    # حالا parent_root را به None تغییر می‌دهیم تا customtkinter تلاشی برای تغییر geometry parent نکند.
    # grab_set همچنان فقط روی پنجره جدید اثر خواهد گذاشت.
    report_win_instance = report_selection_window.ReportSelectionWindow(None, OPEN_TOPLEVEL_WINDOWS, False) 
    
    # اطمینان حاصل می‌کنیم که پنجره قبل از wait_window به صورت کامل initialized شده
    if report_win_instance.winfo_exists():
        report_win_instance.update_idletasks()
        root.wait_window(report_win_instance)
    else:
        print("Warning: ReportSelectionWindow did not get created successfully.")


    # 4. بعد از بسته شدن ReportSelectionWindow، پنجره‌های مینیمایز شده را بازیابی می‌کنیم
    for window in minimized_windows:
        if window.winfo_exists(): # بررسی می‌کنیم که پنجره هنوز وجود دارد
            window.wm_state('normal')
            window.update_idletasks() # اطمینان از رفرش UI


    # 5. ابعاد اصلی پنجره root را بازنشانی می‌کنیم
    root.geometry(f'{ORIGINAL_MAIN_FORM_WIDTH}x{ORIGINAL_MAIN_FORM_HEIGHT}+{int(ORIGINAL_X_POSITION)}+{int(ORIGINAL_Y_POSITION)}')
    root.update_idletasks() # اطمینان از اعمال تغییرات geometry

# فریم افقی برای دکمه‌های اصلی
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

# دکمه نمایش تریدها
tk.Button(button_frame, text="📄 نمایش تریدها",
          command=lambda: show_trades_window(root,
                                            refresh_main_errors_callback=refresh_error_checkboxes,
                                            update_main_timezone_display=update_main_timezone_display_callback,
                                            open_toplevel_windows_list=OPEN_TOPLEVEL_WINDOWS)).pack(side=tk.LEFT, padx=5)


# دکمه ویرایش خطاها (فراخوانی مستقیم و ارسال لیست)
tk.Button(button_frame, text="✏️ ویرایش خطاها", command=lambda: edit_errors_window(open_toplevel_windows_list=OPEN_TOPLEVEL_WINDOWS)).pack(side=tk.LEFT, padx=5)

# دکمه نمایش درصد فراوانی خطاها
tk.Button(button_frame, text="📊 فراوانی خطاها", command=lambda: show_error_frequency_widget(root, open_toplevel_windows_list=OPEN_TOPLEVEL_WINDOWS)).pack(side=tk.LEFT, padx=5)

# دکمه "گزارش جامع" که به سمت راست می‌چسبد
tk.Button(button_frame, text="📊 گزارش جامع",
          command=show_report_selection_window_and_restore_main, # <<< تغییر اینجا
          bg="#A9DFBF", # رنگ پس زمینه متفاوت
          activebackground="#82CBB2" # رنگ هنگام کلیک
          ).pack(side=tk.RIGHT, padx=5) 


# تعداد تریدها
trade_count_label = tk.Label(root, text="📈 تعداد کل تریدها: 0")
trade_count_label.pack(pady=5)
update_trade_count()

# پیام هشدار برای تریدهای تکراری در پایین فرم
warning_message_text = "توجه: در صورتیکه همزمان از ورود دستی و ورود فایل استفاده کنید، برنامه قادر به تشخیص تریدهای تکراری نخواهد بود"
warning_label = tk.Label(root, text=warning_message_text, fg="gray", font=("Vazirmatn", 9), wraplength=430, justify="center")
warning_label.pack(side=tk.BOTTOM, pady=(0, 5))

# اضافه کردن منوی تنظیمات
menubar = tk.Menu(root)
root.config(menu=menubar)

settings_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="تنظیمات", menu=settings_menu)
# فراخوانی توابع از settings_manager (با آرگومان‌های صحیح)
settings_menu.add_command(label="تنظیم منطقه زمانی...", command=lambda: settings_manager.show_timezone_settings_window(root, update_main_timezone_display_callback))
settings_menu.add_command(label="تعیین آستانه ریسک فری...", command=lambda: settings_manager.show_rf_threshold_settings_window(root, update_trade_count, None, None, None))
settings_menu.add_command(label="تنظیم آستانه نمایش فراوانی خطاها...", command=lambda: settings_manager.show_error_frequency_settings_window(root))
# اضافه شدن گزینه جدید به منوی تنظیمات
settings_menu.add_command(label="تنظیم روزهای کاری...", command=lambda: settings_manager.show_working_days_settings_window(root))
# اضافه شدن گزینه جدید به منوی تنظیمات برای سشن‌های معاملاتی
settings_menu.add_command(label="تنظیم سشن‌های معاملاتی...", command=lambda: settings_manager.show_trading_sessions_settings_window(root))

update_main_timezone_display_callback() 

root.mainloop()