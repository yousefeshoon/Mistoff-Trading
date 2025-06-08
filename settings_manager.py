# settings_manager.py

import tkinter as tk
from tkinter import messagebox, ttk
import pytz
from decimal import Decimal, InvalidOperation
import db_manager

def show_timezone_settings_window(parent_root, update_main_timezone_display_callback):
    settings_win = tk.Toplevel(parent_root)
    settings_win.title("تنظیمات منطقه زمانی")
    settings_win.transient(parent_root)
    settings_win.grab_set()
    settings_win.resizable(False, False)

    # Calculate position to center the window relative to parent
    parent_root.update_idletasks() # Ensure geometry is up to date
    root_width = parent_root.winfo_width()
    root_height = parent_root.winfo_height()
    root_x = parent_root.winfo_x()
    root_y = parent_root.winfo_y()

    settings_win_width = 350
    settings_win_height = 100
    x = root_x + (root_width / 2) - (settings_win_width / 2)
    y = root_y + (root_height / 2) - (settings_win_height / 2)
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
            if update_main_timezone_display_callback:
                update_main_timezone_display_callback()
            settings_win.destroy()
        else:
            messagebox.showerror("خطا", "خطایی در ذخیره منطقه زمانی رخ داد.")

    btn_frame_settings = tk.Frame(frame)
    btn_frame_settings.grid(row=2, column=0, columnspan=2, pady=10)

    tk.Button(btn_frame_settings, text="ذخیره", command=save_settings).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame_settings, text="لغو", command=settings_win.destroy).pack(side=tk.LEFT, padx=5)

    settings_win.focus_set()
    settings_win.wait_window(settings_win)

def show_rf_threshold_settings_window(parent_root, update_trade_count_callback, profit_label, loss_label, count_trades_by_type_callback):
    rf_win = tk.Toplevel(parent_root)
    rf_win.title("تنظیم آستانه ریسک فری")
    rf_win.transient(parent_root)
    rf_win.grab_set()
    rf_win.resizable(False, False)

    parent_root.update_idletasks() # Ensure geometry is up to date
    root_width = parent_root.winfo_width()
    root_height = parent_root.winfo_height()
    root_x = parent_root.winfo_x()
    root_y = parent_root.winfo_y()

    rf_win_width = 350
    rf_win_height = 150
    x = root_x + (root_width / 2) - (rf_win_width / 2)
    y = root_y + (root_height / 2) - (rf_win_height / 2)
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
                updated_count = db_manager.recalculate_trade_profits()
                if updated_count > 0:
                    messagebox.showinfo("بروزرسانی تریدها", f"{updated_count} ترید بر اساس آستانه جدید ریسک فری بروزرسانی شد.")
                else:
                    messagebox.showinfo("بروزرسانی تریدها", "هیچ تریدی نیاز به بروزرسانی بر اساس آستانه جدید ریسک فری نداشت.")
                
                # Update main app UI via callbacks
                if update_trade_count_callback:
                    update_trade_count_callback()
                if profit_label and loss_label and count_trades_by_type_callback:
                    profit_count, loss_count = count_trades_by_type_callback()
                    profit_label.config(text=f"تعداد تریدهای سودده: {profit_count}")
                    loss_label.config(text=f"تعداد تریدهای زیان‌ده: {loss_count}")

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

def show_error_frequency_settings_window(parent_root):
    freq_win = tk.Toplevel(parent_root)
    freq_win.title("تنظیم آستانه درصد فراوانی خطا")
    freq_win.transient(parent_root)
    freq_win.grab_set()
    freq_win.resizable(False, False)

    parent_root.update_idletasks() # Ensure geometry is up to date
    root_width = parent_root.winfo_width()
    root_height = parent_root.winfo_height()
    root_x = parent_root.winfo_x()
    root_y = parent_root.winfo_y()

    freq_win_width = 400
    freq_win_height = 150
    x = root_x + (root_width / 2) - (freq_win_width / 2)
    y = root_y + (root_height / 2) - (freq_win_height / 2)
    freq_win.geometry(f'{freq_win_width}x{freq_win_height}+{int(x)}+{int(y)}')

    frame = tk.Frame(freq_win, padx=15, pady=15)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(frame, text="خطاهای با درصد فراوانی کمتر از این مقدار،\nدر ویجت نمایش داده نمی‌شوند:").grid(row=0, column=0, sticky="w", pady=5, padx=5)

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

def update_timezone_display_for_main_app(label_widget):
    """Updates the timezone display label in the main app."""
    current_tz_name = db_manager.get_default_timezone()
    label_widget.config(text=f"⏰ منطقه زمانی فعال: {current_tz_name}")