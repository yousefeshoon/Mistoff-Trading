import tkinter as tk
from tkinter import ttk, messagebox
import db_manager 
from decimal import Decimal 

def show_trades_window(root):
    def load_trades():
        tree.delete(*tree.get_children())
        trades = db_manager.get_all_trades() 
        for row in trades:
            display_values = []
            # اطمینان حاصل می‌کنیم که ترتیب نمایش دقیقاً مطابق با columns تعریف شده باشد
            # و مقادیر Decimal و None را هندل می‌کنیم.
            display_values.append(row['id'])
            display_values.append(row['position_id'] if row['position_id'] is not None else '') 
            display_values.append(row['date'])
            display_values.append(row['time'])
            display_values.append(row['symbol'])
            display_values.append(row['type'] if row['type'] is not None else '') 
            
            # هندل کردن Decimal و None برای size, entry, exit, profit
            size_val = row['size']
            display_values.append(f"{size_val:.2f}" if isinstance(size_val, Decimal) else (''))

            entry_val = row['entry']
            display_values.append(f"{entry_val:.4f}" if isinstance(entry_val, Decimal) else (''))

            exit_val = row['exit']
            display_values.append(f"{exit_val:.4f}" if isinstance(exit_val, Decimal) else (''))
            
            display_values.append(row['profit'])
            display_values.append(row['errors'] if row['errors'] is not None else '')

            tree.insert('', tk.END, values=display_values) 

    def delete_selected():
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("هشدار", "هیچ رکوردی انتخاب نشده است.")
            return
        confirm = messagebox.askyesno("تأیید حذف", "آیا از حذف رکوردهای انتخاب‌شده مطمئن هستید؟")
        if confirm:
            for item in selected_items:
                # شناسه ترید از اولین ستون Treeview (ستون id) گرفته می‌شود
                trade_id = tree.item(item)['values'][0]
                if db_manager.delete_trade(trade_id):
                    pass 
                else:
                    messagebox.showerror("خطا", f"خطا در حذف ترید با شناسه {trade_id} رخ داد.")
            load_trades() 

    def show_edit_errors_popup(parent_window, selected_trade_ids, current_errors_for_single_trade=None):
        """
        پنجره پاپ‌آپ برای ویرایش خطاها را نمایش می‌دهد.
        Args:
            parent_window: پنجره والد (معمولا trades_win).
            selected_trade_ids (list): لیستی از IDهای تریدهای انتخاب شده.
            current_errors_for_single_trade (str, optional): خطاهای فعلی (فقط برای حالت ویرایش تکی).
        """
        popup = tk.Toplevel(parent_window)
        popup.title("ویرایش خطاها")
        popup.transient(parent_window)
        popup.grab_set()
        popup.resizable(False, False)

        # --- شروع تغییرات برای وسط قرار گرفتن پاپ‌آپ ---
        # ابعاد تقریبی پاپ‌آپ
        popup_width = 300
        popup_height = 350 # کمی افزایش برای دکمه‌ها و پدینگ

        # ابعاد صفحه نمایش
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()

        # محاسبه موقعیت x و y برای مرکز
        x = (screen_width / 2) - (popup_width / 2)
        y = (screen_height / 2) - (popup_height / 2)

        popup.geometry(f'{popup_width}x{popup_height}+{int(x)}+{int(y)}')
        # --- پایان تغییرات ---

        errors_frame = tk.Frame(popup, padx=10, pady=10)
        errors_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas و Scrollbar برای لیست چک‌باکس‌ها
        canvas = tk.Canvas(errors_frame, height=200)
        scrollbar = ttk.Scrollbar(errors_frame, orient="vertical", command=canvas.yview)
        
        # حالا Canvas و Scrollbar رو با grid توی errors_frame قرار میدیم
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # پیکربندی ردیف و ستون برای grid
        errors_frame.grid_rowconfigure(0, weight=1)
        errors_frame.grid_columnconfigure(0, weight=1)

        scrollable_frame = tk.Frame(canvas) # این فریم داخل Canvas هست و ویجت‌هاش با pack مدیریت میشن

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        all_errors = db_manager.get_all_errors()
        error_vars = {}
        
        # تعیین خطاهای از پیش انتخاب شده برای حالت تکی
        pre_selected_errors = []
        if len(selected_trade_ids) == 1 and current_errors_for_single_trade:
            pre_selected_errors = [e.strip() for e in current_errors_for_single_trade.split(',') if e.strip()]

        # چک‌باکس‌ها رو مستقیماً توی scrollable_frame با pack اضافه می‌کنیم
        for i, error_name in enumerate(all_errors):
            var = tk.BooleanVar()
            if error_name in pre_selected_errors:
                var.set(True) # در حالت تکی، خطاهای فعلی رو تیک بزن
            chk = tk.Checkbutton(scrollable_frame, text=error_name, variable=var, anchor='w', justify='left')
            chk.pack(anchor='w', padx=5, pady=2) # استفاده از pack
            error_vars[error_name] = var

        # دکمه‌های ذخیره و لغو
        btn_frame_popup = tk.Frame(popup, pady=10)
        btn_frame_popup.pack() # این فریم هم با pack مدیریت میشه و مشکلی با errors_frame نداره

        def save_errors():
            selected_errors = [error for error, var in error_vars.items() if var.get()]
            errors_string_to_save = ", ".join(selected_errors)

            if db_manager.update_trades_errors(selected_trade_ids, errors_string_to_save):
                messagebox.showinfo("موفقیت", "خطاهای انتخاب شده با موفقیت به‌روزرسانی شدند.")
                load_trades() # بروزرسانی Treeview اصلی
                popup.destroy()
            else:
                messagebox.showerror("خطا", "خطایی در به‌روزرسانی خطاها رخ داد.")

        tk.Button(btn_frame_popup, text="ذخیره", command=save_errors).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame_popup, text="لغو", command=popup.destroy).pack(side=tk.LEFT, padx=5)

        popup.focus_set()
        popup.wait_window(popup)

    def edit_selected_errors():
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("هشدار", "هیچ رکوردی انتخاب نشده است.")
            return

        selected_trade_ids = []
        for item in selected_items:
            trade_id = tree.item(item)['values'][0]
            selected_trade_ids.append(trade_id)
        
        if len(selected_trade_ids) == 1:
            # حالت ویرایش تکی
            trade_id = selected_trade_ids[0]
            current_errors = db_manager.get_trade_errors_by_id(trade_id)
            show_edit_errors_popup(trades_win, selected_trade_ids, current_errors)
        else:
            # حالت ویرایش چندتایی
            confirm = messagebox.askyesno("تأیید ویرایش گروهی", 
                                          f"شما {len(selected_trade_ids)} رکورد را انتخاب کرده‌اید. "
                                          "خطاهایی که انتخاب می‌کنید، جایگزین تمام خطاهای قبلی این رکوردها خواهند شد. "
                                          "آیا از ادامه مطمئن هستید؟")
            if confirm:
                show_edit_errors_popup(trades_win, selected_trade_ids) # در این حالت current_errors_for_single_trade نخواهیم داشت
            else:
                messagebox.showinfo("لغو", "عملیات ویرایش گروهی خطاها لغو شد.")

    trades_win = tk.Toplevel(root)
    trades_win.title("همه‌ی تریدها")
    trades_win.geometry("1000x450") 

    tree_frame = tk.Frame(trades_win)
    tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # ترتیب ستون‌ها طبق درخواست قبلی
    columns = ("id", "position_id", "date", "time", "symbol", "type", "size", "entry", "exit", "profit", "errors") 
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")

    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")

    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)

    for col in columns:
        tree.heading(col, text=col.replace("_", " ").title()) 
        # تنظیم عرض ستون‌ها برای نمایش بهتر
        if col == "id":
            tree.column(col, width=40, anchor="center")
        elif col == "position_id": 
            tree.column(col, width=120, anchor="center")
        elif col == "date":
            tree.column(col, width=90, anchor="center")
        elif col == "time":
            tree.column(col, width=60, anchor="center")
        elif col == "symbol":
            tree.column(col, width=70, anchor="center")
        elif col == "type": 
            tree.column(col, width=60, anchor="center")
        elif col == "size": 
            tree.column(col, width=60, anchor="center")
        elif col == "entry":
            tree.column(col, width=80, anchor="center")
        elif col == "exit":
            tree.column(col, width=80, anchor="center")
        elif col == "profit":
            tree.column(col, width=70, anchor="center")
        elif col == "errors":
            tree.column(col, width=250, anchor="w") 
        else:
            tree.column(col, width=80, anchor="center") 

    rtl_text = "\u200f💡 با نگهداشتن دکمه کنترل یا شیفت میتونید چندتایی انتخاب کنید"
    hint_label = tk.Label(trades_win, text=rtl_text, fg="black")
    hint_label.pack(pady=(0, 10))

    btn_frame = tk.Frame(trades_win)
    btn_frame.pack(pady=5)

    del_btn = tk.Button(btn_frame, text="🗑 حذف انتخاب‌شده‌ها", command=delete_selected)
    del_btn.pack(side=tk.LEFT, padx=10)

    refresh_btn = tk.Button(btn_frame, text="🔄 بروزرسانی لیست", command=load_trades)
    refresh_btn.pack(side=tk.LEFT, padx=10)

    edit_errors_btn = tk.Button(btn_frame, text="✏️ ویرایش خطاهای رکورد/ها", command=edit_selected_errors)
    edit_errors_btn.pack(side=tk.LEFT, padx=10)

    load_trades()