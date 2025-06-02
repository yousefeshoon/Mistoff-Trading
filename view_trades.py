# view_trades.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog 
import db_manager 
from decimal import Decimal 
import json 
import os 
import pytz # برای کار با تایم زون
from datetime import datetime

# تابع اصلی برای نمایش پنجره تریدها
def show_trades_window(root, refresh_main_errors_callback=None, update_main_timezone_display=None): # اضافه شدن آرگومان‌ها
    def load_trades():
        tree.delete(*tree.get_children())
        
        # دریافت تایم زون فعال از db_manager برای نمایش
        current_display_timezone = db_manager.get_default_timezone()
        display_message = f"{current_display_timezone} :منطقه زمانی فعال (برای تغییر، به تنظیمات برنامه بروید. تریدها با این منطقه زمانی نمایش داده میشن)"
        current_display_timezone_label.config(text=display_message)

        trades = db_manager.get_all_trades(current_display_timezone) # ارسال تایم زون نمایش
        for row in trades:
            display_values = []
            display_values.append(row['id'])
            display_values.append(row['position_id'] if row['position_id'] is not None else '') 
            display_values.append(row['date'])
            display_values.append(row['time'])
            display_values.append(row['symbol'])
            display_values.append(row['type'] if row['type'] is not None else '') 
            
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
                trade_id = tree.item(item)['values'][0]
                if db_manager.delete_trade(trade_id):
                    pass 
                else:
                    messagebox.showerror("خطا", f"خطا در حذف ترید با شناسه {trade_id} رخ داد.")
            load_trades() 

    def show_edit_errors_popup(parent_window, selected_trade_ids, current_errors_for_single_trade=None):
        popup = tk.Toplevel(parent_window)
        popup.title("ویرایش خطاها")
        popup.transient(parent_window)
        popup.grab_set()
        popup.resizable(False, False)

        popup_width = 300
        popup_height = 350

        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()

        x = (screen_width / 2) - (popup_width / 2)
        y = (screen_height / 2) - (popup_height / 2)

        popup.geometry(f'{popup_width}x{popup_height}+{int(x)}+{int(y)}')

        errors_frame = tk.Frame(popup, padx=10, pady=10)
        errors_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(errors_frame, height=200)
        scrollbar = ttk.Scrollbar(errors_frame, orient="vertical", command=canvas.yview)
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        errors_frame.grid_rowconfigure(0, weight=1)
        errors_frame.grid_columnconfigure(0, weight=1)

        scrollable_frame = tk.Frame(canvas)

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
        
        pre_selected_errors = []
        if len(selected_trade_ids) == 1 and current_errors_for_single_trade:
            pre_selected_errors = [e.strip() for e in current_errors_for_single_trade.split(',') if e.strip()]

        for i, error_name in enumerate(all_errors):
            var = tk.BooleanVar()
            if error_name in pre_selected_errors:
                var.set(True)
            chk = tk.Checkbutton(scrollable_frame, text=error_name, variable=var, anchor='w', justify='left')
            chk.pack(anchor='w', padx=5, pady=2)
            error_vars[error_name] = var

        btn_frame_popup = tk.Frame(popup, pady=10)
        btn_frame_popup.pack()

        def save_errors():
            selected_errors = [error for error, var in error_vars.items() if var.get()]
            errors_string_to_save = ", ".join(selected_errors)

            if db_manager.update_trades_errors(selected_trade_ids, errors_string_to_save):
                messagebox.showinfo("موفقیت", "خطاهای انتخاب شده با موفقیت به‌روزرسانی شدند.")
                load_trades()
                # فراخوانی کال‌بک برای رفرش چک‌باکس‌ها در پنجره اصلی
                if refresh_main_errors_callback:
                    refresh_main_errors_callback()
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
            trade_id = selected_trade_ids[0]
            current_errors = db_manager.get_trade_errors_by_id(trade_id)
            show_edit_errors_popup(trades_win, selected_trade_ids, current_errors)
        else:
            confirm = messagebox.askyesno("تأیید ویرایش گروهی", 
                                          f"شما {len(selected_trade_ids)} رکورد را انتخاب کرده‌اید. "
                                          "خطاهایی که انتخاب می‌کنید، جایگزین تمام خطاهای قبلی این رکوردها خواهند شد. "
                                          "آیا از ادامه مطمئن هستید؟")
            if confirm:
                show_edit_errors_popup(trades_win, selected_trade_ids)
            else:
                messagebox.showinfo("لغو", "عملیات ویرایش گروهی خطاها لغو شد.")

    def export_errors_to_file():
        errors_data = db_manager.get_errors_for_export() 
        
        if not errors_data:
            messagebox.showinfo("اطلاعات", "هیچ خطایی برای خروجی گرفتن وجود ندارد.")
            return

        export_list = []
        for pos_id, errors_str in errors_data:
            export_list.append({"position_id": pos_id, "errors": errors_str})

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json", 
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")], 
            title="ذخیره فایل پشتیبان خطاها" 
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f: 
                    json.dump(export_list, f, ensure_ascii=False, indent=4) 
                messagebox.showinfo("موفقیت", f"خطاها با موفقیت در '{os.path.basename(file_path)}' ذخیره شدند.") 
            except Exception as e:
                messagebox.showerror("خطا", f"خطا در ذخیره فایل: {e}") 
        else:
            messagebox.showinfo("لغو", "عملیات ذخیره فایل پشتیبان خطاها لغو شد.") 

    def import_errors_from_file():
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="انتخاب فایل وارد کردن خطاها"
        )
        if not file_path:
            messagebox.showinfo("لغو", "عملیات وارد کردن خطاها لغو شد.")
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            if not isinstance(imported_data, list):
                messagebox.showerror("خطا", "فرمت فایل نامعتبر است. انتظار لیست دیکشنری‌ها می‌رفت.")
                return

            total_records_in_file = len(imported_data)
            
            confirm_import = messagebox.askyesno("تأیید وارد کردن خطاها",
                                                  f"فایل انتخاب شده حاوی {total_records_in_file} رکورد خطا است.\n"
                                                  "این عملیات خطاهای موجود برای تریدهای هم‌نام را به‌روزرسانی می‌کند و خطاهای جدید را به لیست خطاها اضافه می‌کند.\n"
                                                  "آیا مطمئن هستید که می‌خواهید ادامه دهید؟")
            if not confirm_import:
                messagebox.showinfo("لغو", "وارد کردن خطاها لغو شد.")
                return

            imported_count = db_manager.import_errors_by_position_id(imported_data)
            
            messagebox.showinfo("وارد کردن موفق", 
                                f"{imported_count} ترید با موفقیت به‌روزرسانی شد.\n"
                                f"تعداد کل رکوردهای موجود در فایل: {total_records_in_file}")
            load_trades() 
            # فراخوانی کال‌بک برای رفرش چک‌باکس‌ها در پنجره اصلی
            if refresh_main_errors_callback:
                refresh_main_errors_callback()
            
        except json.JSONDecodeError:
            messagebox.showerror("خطا", "فرمت فایل JSON نامعتبر است.")
        except Exception as e:
            messagebox.showerror("خطا", f"خطا در وارد کردن فایل: {e}")

    class ToolTip:
        def __init__(self, widget, text):
            self.widget = widget
            self.text = text
            self.tip_window = None
            self.id = None
            self.x = self.y = 0
            self.widget.bind("<Enter>", self.enter)
            self.widget.bind("<Leave>", self.leave)

        def enter(self, event=None):
            self.schedule()

        def leave(self, event=None):
            self.unschedule()
            self.hide_tip()

        def schedule(self):
            self.unschedule()
            self.id = self.widget.after(500, self.show_tip)

        def unschedule(self):
            if self.id:
                self.widget.after_cancel(self.id)
                self.id = None

        def show_tip(self):
            if self.tip_window or not self.text:
                return
            x, y, cx, cy = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 20
            
            self.tip_window = tk.Toplevel(self.widget)
            self.tip_window.wm_overrideredirect(True) 
            self.tip_window.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(self.tip_window, text=self.text, justify=tk.LEFT,
                             background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                             font=("tahoma", "8", "normal"), wraplength=250) 
            label.pack(ipadx=1)

        def hide_tip(self):
            if self.tip_window:
                self.tip_window.destroy()
                self.tip_window = None

    trades_win = tk.Toplevel(root)
    trades_win.title("همه‌ی تریدها")
    trades_win.geometry("1000x450") 

    # >>> اضافه شدن لیبل نمایش تایم زون
    current_display_timezone_label = tk.Label(trades_win, text="", fg="blue", font=("Segoe UI", 9, "bold"))
    current_display_timezone_label.pack(pady=(5, 0))
    # <<<

    tree_frame = tk.Frame(trades_win)
    tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

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
    btn_frame.pack(fill=tk.X, pady=5) 

    right_buttons_frame = tk.Frame(btn_frame)
    right_buttons_frame.pack(side=tk.RIGHT, padx=5) 

    del_btn = tk.Button(right_buttons_frame, text="🗑 حذف انتخاب‌شده‌ها", command=delete_selected)
    del_btn.pack(side=tk.LEFT, padx=10)

    refresh_btn = tk.Button(right_buttons_frame, text="🔄 بروزرسانی لیست", command=load_trades)
    refresh_btn.pack(side=tk.LEFT, padx=10)

    edit_errors_btn = tk.Button(right_buttons_frame, text="✏️ ویرایش خطاهای رکورد/ها", command=edit_selected_errors)
    edit_errors_btn.pack(side=tk.LEFT, padx=10)

    left_buttons_frame = tk.Frame(btn_frame) 
    left_buttons_frame.pack(side=tk.LEFT, padx=5) 

    export_errors_btn = tk.Button(left_buttons_frame, text="⬇️ بک‌آپ خطاها", command=export_errors_to_file)
    export_errors_btn.pack(side=tk.LEFT, padx=10) 
    
    tooltip_text_export = (
        "میتونید از کلیه رکوردهایی که بهشون خطاهای مختلف اضافه کردید بک آپ بگیرید "
        "تا اگر مشکلی برای دیتابیس بوجود اومد، به سادگی همه چیز رو برگردونید سرجای خودش.\n"
        "اطلاعات شما مهم هستن."
    )
    ToolTip(export_errors_btn, tooltip_text_export)

    import_errors_btn = tk.Button(left_buttons_frame, text="⬆️ ایمپورت بک‌آپ خطاها ", command=import_errors_from_file)
    import_errors_btn.pack(side=tk.LEFT, padx=10) 

    tooltip_text_import = (
        "با استفاده از فایل بک‌آپ خطاها، می‌توانید خطاهای تریدهای قبلی را "
        "به صورت خودکار به تریدهای موجود (بر اساس Position ID) اضافه کنید."
    )
    ToolTip(import_errors_btn, tooltip_text_import)

    load_trades()