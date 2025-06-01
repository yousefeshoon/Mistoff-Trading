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
            display_values.append(row['position_id'] if row['position_id'] is not None else '') # برای position_id
            display_values.append(row['date'])
            display_values.append(row['time'])
            display_values.append(row['symbol'])
            display_values.append(row['type'] if row['type'] is not None else '') # برای type
            
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

    load_trades()