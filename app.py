import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from tkcalendar import DateEntry
import os
import version_info
import sys

# تابع کمکی برای پیدا کردن مسیر فایل‌ها در حالت کامپایل‌شده
def get_resource_path(relative_path):
    """
    مسیر صحیح یک فایل را در محیط توسعه یا پس از کامپایل با PyInstaller برمی‌گرداند.
    """
    if hasattr(sys, '_MEIPASS'): # اگر برنامه با PyInstaller کامپایل شده باشد
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# حالا آیکون را با استفاده از این تابع بارگذاری می‌کنیم
#root.iconbitmap(os.path.join(os.path.dirname(__file__), "icon.ico"))#این خط رو به زیر تغییر بده

# ایمپورت کردن ماژول‌های خودت
# دقت کن: دیگه sqlite3 رو اینجا ایمپورت نمی‌کنیم
import db_manager
from view_trades import show_trades_window
from error_widget import show_error_frequency_widget # اینو بعداً باید تغییر بدیم
from tkinter import simpledialog

db_manager.migrate_database() # حالا برای اطمینان از به روز بودن دیتابیس، migrate_database را صدا می‌زنیم

# حالا APP_VERSION رو از version_info.py می‌خونیم
APP_VERSION = version_info.__version__


# ساخت پنجره اصلی
root = tk.Tk()
root.iconbitmap(os.path.join(os.path.dirname(__file__), "icon.ico")) # قرار دادن آیکون در تایتل بار - این خط رو خودت باید بررسی کنی
root.title(f"Trade Journal - {APP_VERSION}") # نسخه برنامه در عنوان پنجره
root.geometry("450x650")

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
    selected_errors = [error for error, var in error_vars.items() if var.get()]
    
    # بررسی خالی بودن فیلد تایم
    if not time:
        messagebox.showerror("Missing Time", "لطفاً ساعت معامله را وارد کنید.")
        return

    # بررسی تکراری بودن ترکیب تاریخ و ساعت
    # حالا از db_manager استفاده می‌کنیم
    if db_manager.check_duplicate_trade(date, time):
        messagebox.showerror("Duplicate Entry", "تریدی با این تاریخ و ساعت قبلاً ثبت شده است")
        return
        
    # اگر Loss انتخاب شده، باید حداقل یک خطا تیک خورده باشه
    if profit == "Loss" and not selected_errors:
        messagebox.showerror("Missing Error", "برای ترید ضررده، حداقل یک خطا باید انتخاب شود.")
        return

    # ذخیره ترید جدید - حالا از db_manager استفاده می‌کنیم
    # دقت کن که 'exit' تابع داخلی پایتون هست، بهتره اسم متغیر رو عوض کنیم. من اینجا به exit_price تغییر دادم.
    if not db_manager.add_trade(date, time, symbol, 
                                 entry if entry else None, 
                                 exit_price if exit_price else None, 
                                 profit, 
                                 ', '.join(selected_errors),
                                 float(size) if size else 0.0):
        messagebox.showerror("خطا", "خطایی در ذخیره ترید رخ داد.")
        return
    
    # ذخیره ایرادات جدید در جدول خطاها
    # این عملیات هم به db_manager منتقل شد
    for error in selected_errors:
        db_manager.add_error_to_list(error) # تابع جدید در db_manager

    messagebox.showinfo("Saved", "Trade saved successfully.")
    update_trade_count() # این تابع هم باید از db_manager استفاده کنه
    
    # بروزرسانی شمارنده‌ها
    profit_count, loss_count = count_trades_by_type() # این تابع هم باید از db_manager استفاده کنه
    profit_label.config(text=f"تعداد تریدهای سودده: {profit_count}")
    loss_label.config(text=f"تعداد تریدهای زیان‌ده: {loss_count}")

    # پاک‌سازی فیلدها به جز تاریخ
    entry_time.delete(0, tk.END)
    # entry_symbol.delete(0, tk.END) # می‌تونی این خط رو کامنت بذاری یا حذف کنی اگه نمی‌خوای US30 پاک بشه
    entry_entry.delete(0, tk.END)
    entry_exit.delete(0, tk.END)
    profit_var.set("Profit") # بعد از ذخیره، به حالت پیش‌فرض برگرده
    for var in error_vars.values(): # دقت کن که .values() اضافه کردم
        var.set(False)


def clear_fields():
    entry_date.set_date('') 
    entry_time.delete(0, tk.END)
    entry_symbol.delete(0, tk.END)
    entry_symbol.insert(0, "US30")
    entry_entry.delete(0, tk.END)
    entry_exit.delete(0, tk.END)
    entry_size.delete(0, tk.END) # اضافه کردن این خط
    profit_var.set("Profit")
    for var in error_vars.values(): # دقت کن که .values() اضافه کردم
        var.set(False)

'''def add_error():
    new_error = entry_new_error.get().strip()
    if not new_error:
        return
    
    # حالا از db_manager استفاده می‌کنیم
    if db_manager.add_error_to_list(new_error):
        refresh_error_checkboxes()
        entry_new_error.delete(0, tk.END)
    else:
        messagebox.showwarning("Warning", "Error already exists or an error occurred.")
'''

def load_errors():
    # حالا از db_manager استفاده می‌کنیم
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

# تابع نمایش تعداد تریدها
def update_trade_count():
    # حالا از db_manager استفاده می‌کنیم
    count = db_manager.get_total_trades_count()
    trade_count_label.config(text=f"📈 تعداد تریدها: {count}")

# تعداد تریدهای سودده و زیان ده    
def count_trades_by_type():
    # حالا از db_manager استفاده می‌کنیم
    profit_count = db_manager.get_profit_trades_count()
    loss_count = db_manager.get_loss_trades_count()
    return profit_count, loss_count

# لیبل و ورودی‌ها در یک گرید مرتب
def add_labeled_entry(row, label_text, widget):
    label = tk.Label(main_frame, text=label_text, anchor='e', width=15)
    label.grid(row=row, column=0, padx=5, pady=5, sticky='e')
    widget.grid(row=row, column=1, padx=5, pady=5, sticky='w')

# ویرایش خطاها
def edit_errors_window():
    window = tk.Toplevel(root)
    window.title("ویرایش خطاها")
    window.geometry("400x480") # ارتفاع پنجره را کمی افزایش دادم

    # فریم اصلی محتوا (بالا تا پایین)
    main_edit_frame = tk.Frame(window)
    main_edit_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # 1. بخش Treeview (با قابلیت گسترش)
    tree_section_frame = tk.Frame(main_edit_frame)
    tree_section_frame.pack(fill=tk.BOTH, expand=True) # این فریم فضای میانی را اشغال می‌کند

    tree = ttk.Treeview(tree_section_frame, columns=("Error", "Count"), show="headings", height=15)
    tree.heading("Error", text="عنوان خطا")
    tree.heading("Count", text="تعداد استفاده")
    tree.pack(fill=tk.BOTH, expand=True) # Treeview داخل این فریم گسترش می‌یابد

    # 2. بخش دکمه‌های حذف و تغییر عنوان
    btn_frame = tk.Frame(main_edit_frame)
    btn_frame.pack(pady=5) # این فریم زیر Treeview قرار می‌گیرد

    # 3. بخش افزودن خطای جدید
    add_error_section_frame = tk.Frame(main_edit_frame)
    add_error_section_frame.pack(pady=10) # این فریم زیر دکمه‌های حذف/تغییر عنوان قرار می‌گیرد

    # -------------------------------------------------------------
    # تعریف توابع داخلی (refresh_edit_errors_treeview, delete_selected, rename_selected, add_new_error_from_edit_window)
    # این توابع را در اینجا تعریف می‌کنیم تا به ویجت‌های بالا دسترسی داشته باشند.
    # -------------------------------------------------------------

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
            refresh_error_checkboxes() # چک‌باکس‌ها رو بروزرسانی کن
            refresh_edit_errors_treeview() # بعد از حذف، جدول ویرایش خطاها را هم بروزرسانی کن
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
            refresh_error_checkboxes() # چک‌باکس‌ها رو بروزرسانی کن
            refresh_edit_errors_treeview() # بعد از تغییر نام، جدول ویرایش خطاها را هم بروزرسانی کن
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
            refresh_edit_errors_treeview() # بروزرسانی Treeview در پنجره ویرایش
            refresh_error_checkboxes() # بروزرسانی چک‌باکس‌های فرم اصلی
            new_error_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("هشدار", "این خطا قبلاً وجود دارد یا خطایی در ذخیره رخ داد.")
            print(f"خطا در افزودن '{new_error}': یا تکراری بود یا مشکل دیتابیس.")

    # -------------------------------------------------------------
    # پک کردن ویجت‌ها در فریم‌ها (بعد از تعریف توابع)
    # -------------------------------------------------------------

    # ویجت‌های بخش دکمه‌های حذف و تغییر عنوان
    tk.Button(btn_frame, text="🗑 حذف", command=delete_selected).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="✏️ تغییر عنوان", command=rename_selected).pack(side=tk.LEFT, padx=5)

    # ویجت‌های بخش افزودن خطای جدید
    tk.Label(add_error_section_frame, text="", anchor='w').pack(side=tk.LEFT, padx=5)
    new_error_entry = tk.Entry(add_error_section_frame, width=30)
    new_error_entry.pack(side=tk.LEFT, padx=5)
    tk.Button(add_error_section_frame, text="➕ اضافه کردن", command=add_new_error_from_edit_window).pack(side=tk.LEFT, padx=5)

    refresh_edit_errors_treeview() # بارگذاری اولیه جدول خطاها


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

# قیمت ورود
entry_entry = tk.Entry(main_frame, width=30)
add_labeled_entry(3, "Entry (optional):", entry_entry)

# قیمت خروج
entry_exit = tk.Entry(main_frame, width=30)
add_labeled_entry(4, "Exit (optional):", entry_exit)

# Size
entry_size = tk.Entry(main_frame, width=30)
add_labeled_entry(5, "Size (optional):", entry_size) # سطر 5 برای Size

# سود/ضرر/RF
profit_var = tk.StringVar()
profit_dropdown = ttk.Combobox(main_frame, textvariable=profit_var, values=["Profit", "Loss", "RF"], width=27)
profit_dropdown.current(0)
add_labeled_entry(6, "Profit / RF / Loss:", profit_dropdown)

# افزودن ایراد جدید
#entry_new_error = tk.Entry(main_frame, width=30)
#add_labeled_entry(6, "Add New Error:", entry_new_error)

#btn_add_error = tk.Button(main_frame, text="Add", command=add_error, width=10)
#btn_add_error.grid(row=6, column=2, padx=5)

# لیست چک‌باکس ایرادات
tk.Label(main_frame, text="Select Errors:", anchor='w').grid(row=7, column=0, sticky='ne', padx=5, pady=(10, 0))
error_frame = tk.Frame(main_frame)
error_frame.grid(row=7, column=1, columnspan=2, sticky='w', pady=(10, 0))
error_names = []
error_vars = {}
refresh_error_checkboxes() # حتماً بعد از ساخت error_frame صدا زده بشه

# دکمه ذخیره
btn_save = tk.Button(main_frame, text="Save Trade", command=save_trade, width=20)
btn_save.grid(row=8, column=0, columnspan=3, pady=20)

# فریم افقی برای دکمه‌ها
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

# دکمه نمایش تریدها
tk.Button(button_frame, text="📄 نمایش تریدها", command=lambda: show_trades_window(root)).pack(side=tk.LEFT, padx=5)

# دکمه نمایش درصد فراوانی خطاها
# توجه: این تابع هنوز مستقل نیست. بعداً باید اصلاحش کنیم.
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
update_trade_count() # بار اول مقداردهی می‌کنه


root.mainloop()