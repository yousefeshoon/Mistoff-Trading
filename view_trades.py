import tkinter as tk
from tkinter import ttk, messagebox
# دیگه نیازی به ایمپورت sqlite3 نیست
import db_manager # ماژول جدید db_manager رو ایمپورت می‌کنیم

def show_trades_window(root):
    def load_trades():
        tree.delete(*tree.get_children())
        # حالا از db_manager استفاده می‌کنیم
        trades = db_manager.get_all_trades()
        for row in trades:
            # row.values() برای اینه که دیگه row به صورت sqlite3.Row برگردونده میشه
            # و می‌تونه مستقیماً به values() در tree.insert داده بشه.
            # البته می‌تونیم column به column هم دسترسی داشته باشیم مثل row['id']
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
                # حالا از db_manager استفاده می‌کنیم
                if db_manager.delete_trade(trade_id):
                    # اگر حذف موفقیت‌آمیز بود، فقط پیام می‌دهیم و لیست را رفرش می‌کنیم
                    pass 
                else:
                    messagebox.showerror("خطا", f"خطا در حذف ترید با شناسه {trade_id} رخ داد.")
            load_trades() # بعد از حذف، لیست رو دوباره بارگذاری می‌کنیم

    # دیگه نیازی به این خطوط اتصال مستقیم به دیتابیس نیست
    # conn = sqlite3.connect("trades.db")
    # cursor = conn.cursor()

    trades_win = tk.Toplevel(root)
    trades_win.title("همه‌ی تریدها")
    trades_win.geometry("950x450")

    columns = ("id", "date", "time", "symbol", "entry", "exit", "size", "profit", "errors") # size اضافه شد
    tree = ttk.Treeview(trades_win, columns=columns, show="headings", selectmode="extended")

    for col in columns:
        tree.heading(col, text=col)
         # تنظیم عرض ستون‌ها
        if col == "errors":
            tree.column(col, width=300)
        elif col == "size": # اضافه کردن تنظیم عرض برای size
            tree.column(col, width=60)
        else:
            tree.column(col, width=100)

    tree.column("id", width=50)  # ID کوچکتر

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


# این بخش (if __name__ == "__main__":) رو می‌تونی برای تست ماژول به تنهایی نگه داری
# اما وقتی app.py برنامه اصلیه، نیازی بهش نیست و در نهایت حذف میشه یا تغییر می‌کنه.
#if __name__ == "__main__":
#    root = tk.Tk()
#    root.withdraw()  # فرم اصلی رو نشون نده
#    show_trades_window(root)
#    root.mainloop()