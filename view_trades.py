import tkinter as tk
from tkinter import ttk, messagebox
import db_manager 

def show_trades_window(root):
    def load_trades():
        tree.delete(*tree.get_children())
        trades = db_manager.get_all_trades() # حالا db_manager.get_all_trades() ترتیب ستون‌ها رو بر اساس نیاز ما برمی‌گردونه
        for row in trades:
            # list(row) به صورت پیش‌فرض مقادیر رو به همون ترتیبی که در SELECT هستن، برمی‌گردونه.
            tree.insert('', tk.END, values=list(row)) 

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

    trades_win = tk.Toplevel(root)
    trades_win.title("همه‌ی تریدها")
    trades_win.geometry("1000x450") 

    # **تغییر اصلی در این تابع:**
    # تعریف ستون‌ها با ترتیب جدید برای نمایش،
    # که دقیقاً با خروجی `db_manager.get_all_trades()` (ترتیب دیتابیس) مطابقت دارد.
    columns = ("id", "date", "time", "symbol", "entry", "exit", "profit", "errors", "size", "position_id", "type") 
    tree = ttk.Treeview(trades_win, columns=columns, show="headings", selectmode="extended")

    for col in columns:
        tree.heading(col, text=col)
        # تنظیم عرض ستون‌ها برای نمایش بهتر
        if col == "id":
            tree.column(col, width=40, anchor="center")
        elif col == "date":
            tree.column(col, width=90, anchor="center")
        elif col == "time":
            tree.column(col, width=60, anchor="center")
        elif col == "symbol":
            tree.column(col, width=70, anchor="center")
        elif col == "entry":
            tree.column(col, width=80, anchor="center")
        elif col == "exit":
            tree.column(col, width=80, anchor="center")
        elif col == "profit":
            tree.column(col, width=70, anchor="center")
        elif col == "errors":
            tree.column(col, width=250, anchor="w") 
        elif col == "size": # حالا size اینجا هست
            tree.column(col, width=60, anchor="center")
        elif col == "position_id":
            tree.column(col, width=120, anchor="center") 
        elif col == "type": # حالا type اینجا هست
            tree.column(col, width=60, anchor="center")
        else:
            tree.column(col, width=80, anchor="center") 

    tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

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