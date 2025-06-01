import tkinter as tk
from tkinter import messagebox, filedialog 
from tkinter import ttk
from tkcalendar import DateEntry
import os
import version_info
import sys

# ایمپورت ماژول mt5_importer
import mt5_importer 

# تابع کمکی برای پیدا کردن مسیر فایل‌ها در حالت کامپایل‌شده
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

# ساخت پنجره اصلی
root = tk.Tk()
root.iconbitmap(os.path.join(os.path.dirname(__file__), "icon.ico")) 
root.title(f"MistOff Trading - {APP_VERSION}") 
root.geometry("450x700") 

main_frame = tk.Frame(root)
main_frame.pack(padx=10, pady=10)

def save_trade(event=None):
    date = entry_date.get()
    time = entry_time.get()
    symbol = entry_symbol.get()
    entry = entry_entry.get()
    exit_price = entry_exit.get()
    size = entry_size.get()
    profit = profit_var.get()
    
    trade_type = trade_type_var.get() 

    selected_errors = [error for error, var in error_vars.items() if var.get()]
    
    if not time:
        messagebox.showerror("Missing Time", "لطفاً ساعت معامله را وارد کنید.")
        return

    if db_manager.check_duplicate_trade(date, time):
        messagebox.showerror("Duplicate Entry", "تریدی با این تاریخ و ساعت قبلاً ثبت شده است")
        return
        
    if profit == "Loss" and not selected_errors:
        messagebox.showerror("Missing Error", "برای ترید ضررده، حداقل یک خطا باید انتخاب شود.")
        return

    if not db_manager.add_trade(date, time, symbol, 
                                 entry if entry else None, 
                                 exit_price if exit_price else None, 
                                 profit, 
                                 ', '.join(selected_errors),
                                 float(size) if size else 0.0,
                                 position_id=None, 
                                 trade_type=trade_type): 
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
        print("بروزرسانی جدول ویرایش خطاها...")
        for item in tree.get_children():
            tree.delete(item)
        
        errors_from_db = db_manager.get_all_errors_with_id()
        error_counts = db_manager.get_error_usage_counts()

        print(f"تعداد خطاها از دیتابیس: {len(errors_from_db)}")

        for eid, err_text in errors_from_db:
            count = error_counts.get(err_text, 0)
            tree.insert("", "end", iid=str(eid), values=(err_text, count))
            print(f"اضافه کردن به جدول: ID={eid}, خطا='{err_text}', تعداد={count}")
        print("جدول بروزرسانی شد.")

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
        
        print(f"تلاش برای افزودن خطا: '{new_error}'")
        result = db_manager.add_error_to_list(new_error)
        
        if result:
            messagebox.showinfo("موفقیت", "خطا با موفقیت اضافه شد.")
            print(f"خطا '{new_error}' با موفقیت اضافه شد.")
            refresh_edit_errors_treeview() 
            refresh_error_checkboxes() 
            new_error_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("هشدار", "این خطا قبلاً وجود دارد یا خطایی در ذخیره رخ داد.")
            print(f"خطا در افزودن '{new_error}': یا تکراری بود یا مشکل دیتابیس.")

    tk.Button(btn_frame, text="🗑 حذف", command=delete_selected).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="✏️ تغییر عنوان", command=rename_selected).pack(side=tk.LEFT, padx=5)

    tk.Label(add_error_section_frame, text="", anchor='w').pack(side=tk.LEFT, padx=5)
    new_error_entry = tk.Entry(add_error_section_frame, width=30)
    new_error_entry.pack(side=tk.LEFT, padx=5)
    tk.Button(add_error_section_frame, text="➕ اضافه کردن", command=add_new_error_from_edit_window).pack(side=tk.LEFT, padx=5)

    refresh_edit_errors_treeview() 

# تابع تغییر نام داده شده و فیلتر فایل‌ها به xlsx تغییر یافت.
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

# تابع تغییر نام داده شده است.
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
        # استفاده از mt5_importer برای پردازش فایل اکسل
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
# تغییر LabelFrame از "HTML" به "گزارش MT5"
report_import_frame = tk.LabelFrame(root, text="وارد کردن از گزارش MT5 (اکسل)") 
report_import_frame.pack(padx=10, pady=10, fill=tk.X)

# تغییر نام متغیر از html_file_path_var به report_file_path_var
report_file_path_var = tk.StringVar() 

tk.Label(report_import_frame, text="فایل گزارش اکسل:", anchor='w').grid(row=0, column=0, padx=5, pady=5, sticky='w')

# تغییر نام Entry از html_path_entry به report_path_entry
report_path_entry = tk.Entry(report_import_frame, textvariable=report_file_path_var, width=40, state='readonly') 
report_path_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

# تغییر تابع فراخوانی شده از select_html_file به select_report_file
select_file_btn = tk.Button(report_import_frame, text="انتخاب فایل...", command=select_report_file)
select_file_btn.grid(row=0, column=2, padx=5, pady=5)

# تغییر نام دکمه و تابع فراخوانی شده
import_report_btn = tk.Button(report_import_frame, text="وارد کردن از گزارش", command=import_trades_from_report) 
import_report_btn.grid(row=1, column=0, columnspan=3, pady=5)


# فریم افقی برای دکمه‌های اصلی (نمایش تریدها و فراوانی خطاها)
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

# دکمه نمایش تریدها
tk.Button(button_frame, text="📄 نمایش تریدها", command=lambda: show_trades_window(root)).pack(side=tk.LEFT, padx=5)

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
warning_label.pack(side=tk.BOTTOM, pady=(0, 5)) # چسبیده به پایین با کمی پدینگ از بالا

root.mainloop()