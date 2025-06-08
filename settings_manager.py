# settings_manager.py

import tkinter as tk
from tkinter import messagebox, ttk
import pytz
from decimal import Decimal, InvalidOperation
from datetime import datetime, time 
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
                
                # Update main app UI via callbacks (profit/loss labels are removed)
                if update_trade_count_callback:
                    update_trade_count_callback()

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


def show_working_days_settings_window(parent_root):
    wd_win = tk.Toplevel(parent_root)
    wd_win.title("تنظیم روزهای کاری")
    wd_win.transient(parent_root)
    wd_win.grab_set()
    wd_win.resizable(False, False)

    parent_root.update_idletasks()
    root_width = parent_root.winfo_width()
    root_height = parent_root.winfo_height()
    root_x = parent_root.winfo_x()
    root_y = parent_root.winfo_y()

    wd_win_width = 350
    wd_win_height = 250 
    x = root_x + (root_width / 2) - (wd_win_width / 2)
    y = root_y + (root_height / 2) - (wd_win_height / 2)
    wd_win.geometry(f'{wd_win_width}x{wd_win_height}+{int(x)}+{int(y)}')

    frame = tk.Frame(wd_win, padx=15, pady=15)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(frame, text="روزهای کاری هفته را انتخاب کنید (روز آغازین هفته شما: دوشنبه):", anchor='w').pack(pady=(0, 10), fill='x')

    day_names_persian = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]
    python_weekday_order = [0, 1, 2, 3, 4, 5, 6] 

    day_vars = {}
    current_working_days = db_manager.get_working_days()

    for i, day_name in enumerate(day_names_persian):
        python_day_index = python_weekday_order[i] 
        
        var = tk.BooleanVar()
        if python_day_index in current_working_days:
            var.set(True)
        
        chk = tk.Checkbutton(frame, text=day_name, variable=var, anchor='w')
        chk.pack(anchor='w', padx=5, pady=2)
        day_vars[python_day_index] = var 

    def save_working_days():
        selected_days = [day_index for day_index, var in day_vars.items() if var.get()]
        
        if db_manager.set_working_days(selected_days):
            messagebox.showinfo("موفقیت", "روزهای کاری با موفقیت ذخیره شدند.")
            wd_win.destroy()
        else:
            messagebox.showerror("خطا", "خطایی در ذخیره روزهای کاری رخ داد.")

    btn_frame_wd_settings = tk.Frame(frame)
    btn_frame_wd_settings.pack(pady=10)

    tk.Button(btn_frame_wd_settings, text="ذخیره", command=save_working_days).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame_wd_settings, text="لغو", command=wd_win.destroy).pack(side=tk.LEFT, padx=5)

    wd_win.focus_set()
    wd_win.wait_window(wd_win)

# <<< تابع جدید برای تنظیمات سشن‌های معاملاتی
def show_trading_sessions_settings_window(parent_root):
    sessions_win = tk.Toplevel(parent_root)
    sessions_win.title("تنظیم سشن‌های معاملاتی")
    sessions_win.transient(parent_root)
    sessions_win.grab_set()
    sessions_win.resizable(False, False)

    parent_root.update_idletasks()
    root_width = parent_root.winfo_width()
    root_height = parent_root.winfo_height()
    root_x = parent_root.winfo_x()
    root_y = parent_root.winfo_y()

    sessions_win_width = 450
    sessions_win_height = 400 
    x = root_x + (root_width / 2) - (sessions_win_width / 2)
    y = root_y + (root_height / 2) - (sessions_win_height / 2)
    sessions_win.geometry(f'{sessions_win_width}x{sessions_win_height}+{int(x)}+{int(y)}')

    frame = tk.Frame(sessions_win, padx=15, pady=15)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(frame, text="زمان‌های شروع و پایان سشن‌های معاملاتی را بر اساس منطقه زمانی خودتان وارد کنید:").pack(pady=(0, 10), fill='x')
    tk.Label(frame, text=f"منطقه زمانی فعال شما: {db_manager.get_default_timezone()}", font=("Segoe UI", 9, "italic")).pack(pady=(0, 5), fill='x')
    tk.Label(frame, text="برنامه به طور خودکار تغییرات ساعت تابستانی (DST) را مدیریت می‌کند.", font=("Segoe UI", 8, "italic"), fg="gray").pack(pady=(0, 10), fill='x')

    # فریم جدید برای نگه داشتن ورودی‌های سشن با Grid
    sessions_input_frame = tk.Frame(frame, bg="white") # <<< فریم جدید
    sessions_input_frame.pack(fill='both', expand=True, pady=10) # <<< با pack در فریم اصلی قرار می‌گیرد

    # پیکربندی ستون‌ها برای Grid در sessions_input_frame
    sessions_input_frame.grid_columnconfigure(0, weight=1) # برای لیبل نام سشن
    sessions_input_frame.grid_columnconfigure(1, weight=1) # برای Entry شروع
    sessions_input_frame.grid_columnconfigure(2, weight=0) # برای لیبل "تا"
    sessions_input_frame.grid_columnconfigure(3, weight=1) # برای Entry پایان

    session_names = {
        'ny': 'نیویورک',
        'sydney': 'سیدنی',
        'tokyo': 'توکیو',
        'london': 'لندن'
    }
    
    session_entries = {}
    current_session_times_utc = db_manager.get_session_times_utc()
    user_tz = pytz.timezone(db_manager.get_default_timezone())

    row_idx = 0
    for key, name in session_names.items():
        start_utc_str = current_session_times_utc[key]['start']
        end_utc_str = current_session_times_utc[key]['end']

        try:
            # تبدیل زمان UTC ذخیره‌شده به زمان کاربر برای نمایش
            start_utc_time = datetime.strptime(start_utc_str, '%H:%M').time()
            end_utc_time = datetime.strptime(end_utc_str, '%H:%M').time()

            # برای تبدیل DST-aware، نیاز به یک datetime object با تاریخ داریم
            # تاریخ امروز (در UTC) را به عنوان مبنا قرار می‌دهیم.
            today_utc_naive = datetime.utcnow().replace(hour=start_utc_time.hour, minute=start_utc_time.minute, second=0, microsecond=0)
            today_utc_aware = pytz.utc.localize(today_utc_naive)
            start_display_aware = today_utc_aware.astimezone(user_tz)
            start_display_str = start_display_aware.strftime('%H:%M')

            today_utc_naive = datetime.utcnow().replace(hour=end_utc_time.hour, minute=end_utc_time.minute, second=0, microsecond=0)
            today_utc_aware = pytz.utc.localize(today_utc_naive)
            end_display_aware = today_utc_aware.astimezone(user_tz)
            end_display_str = end_display_aware.strftime('%H:%M')
            
        except ValueError:
            start_display_str = start_utc_str # اگر فرمت اشتباه بود، UTC خام نمایش داده شود
            end_display_str = end_utc_str
        except Exception as e:
            print(f"Error converting session time for display ({key}): {e}") # چاپ خطا برای دیباگ
            start_display_str = "Error"
            end_display_str = "Error"

        # استفاده از grid در sessions_input_frame
        tk.Label(sessions_input_frame, text=f"{name}:", anchor='e', bg="white").grid(row=row_idx, column=0, sticky='ew', pady=5, padx=5)
        
        start_var = tk.StringVar(value=start_display_str)
        start_entry = tk.Entry(sessions_input_frame, textvariable=start_var, width=8)
        start_entry.grid(row=row_idx, column=1, sticky='w', pady=5, padx=5)
        
        tk.Label(sessions_input_frame, text="تا", anchor='center', bg="white").grid(row=row_idx, column=2, sticky='ew', pady=5, padx=5)
        
        end_var = tk.StringVar(value=end_display_str)
        end_entry = tk.Entry(sessions_input_frame, textvariable=end_var, width=8)
        end_entry.grid(row=row_idx, column=3, sticky='w', pady=5, padx=5)
        
        session_entries[key] = {'start_var': start_var, 'end_var': end_var}
        row_idx += 1
    
    def save_sessions():
        new_session_data_utc = {}
        for key, vars_dict in session_entries.items():
            start_str = vars_dict['start_var'].get().strip()
            end_str = vars_dict['end_var'].get().strip()

            # اعتبارسنجی فرمت زمان
            try:
                start_time_naive = datetime.strptime(start_str, '%H:%M').time()
                end_time_naive = datetime.strptime(end_str, '%H:%M').time()
            except ValueError:
                messagebox.showerror("خطا", "لطفاً زمان را با فرمت HH:MM وارد کنید (مثلاً 09:30).")
                return

            # تبدیل زمان کاربر (در تایم زون انتخابی) به UTC برای ذخیره
            user_tz = pytz.timezone(db_manager.get_default_timezone())
            # از تاریخ امروز UTC استفاده می‌کنیم تا DST برای زمان‌های وارد شده کاربر به درستی اعمال شود
            today_utc_date = datetime.utcnow().date() 
            
            # Combine current date with user input time, then localize to user_tz, then convert to UTC
            start_dt_user_naive = datetime.combine(today_utc_date, start_time_naive) # Use today's date in UTC for accurate DST conversion
            # باید زمان ورودی کاربر رو به تایم زون خودش localize کنیم، بعد به UTC تبدیل کنیم.
            # اگر زمان وارد شده توسط کاربر در یک تاریخ خاص باشه که DST اتفاق میفته، pytz خودش تنظیمات رو انجام میده.
            
            # برای تبدیل دقیق‌تر از زمان ورودی کاربر (HH:MM در تایم زون خودش) به UTC
            # یک تاریخ پایه (مثلاً 2024-01-01) را در تایم زون کاربر آگاه می‌کنیم
            # این روش برای DST در زمان‌های مرزی هم دقیق‌تر است.
            # به جای datetime.now().date() که ممکنه تاریخش رو از سیستم بگیره،
            # بهتره یک تاریخ ثابت و دلخواه (مثلاً Jan 1st 2024) در نظر بگیریم.
            # یا برای سادگی، تاریخ امروز کاربر رو در تایم زون خودش بگیریم.
            
            # برای ساده‌سازی و دقیق‌تر کردن:
            # زمان‌های hh:mm از کاربر رو در تایم زون کاربر (با تاریخ today)
            # به یک datetime object تبدیل می‌کنیم و بعد به UTC.
            
            # Use current date as basis for timezone conversion to handle DST correctly.
            current_date_in_user_tz = datetime.now(user_tz).date() # تاریخ امروز در تایم زون کاربر

            start_dt_user_naive = datetime.combine(current_date_in_user_tz, start_time_naive)
            start_dt_user_aware = user_tz.localize(start_dt_user_naive, is_dst=None) # is_dst=None برای خودکار تشخیص DST
            start_utc_aware = start_dt_user_aware.astimezone(pytz.utc)
            
            end_dt_user_naive = datetime.combine(current_date_in_user_tz, end_time_naive)
            end_dt_user_aware = user_tz.localize(end_dt_user_naive, is_dst=None)
            end_utc_aware = end_dt_user_aware.astimezone(pytz.utc)

            new_session_data_utc[key] = {
                'start': start_utc_aware.strftime('%H:%M'),
                'end': end_utc_aware.strftime('%H:%M')
            }
        
        if db_manager.set_session_times_utc(new_session_data_utc):
            messagebox.showinfo("موفقیت", "ساعت‌های سشن با موفقیت ذخیره شدند.")
            sessions_win.destroy()
        else:
            messagebox.showerror("خطا", "خطایی در ذخیره ساعت‌های سشن رخ داد.")

    btn_frame_sessions = tk.Frame(frame)
    btn_frame_sessions.pack(pady=10) # این فریم با pack چیده می‌شود

    tk.Button(btn_frame_sessions, text="ذخیره", command=save_sessions).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame_sessions, text="لغو", command=sessions_win.destroy).pack(side=tk.LEFT, padx=5)

    sessions_win.focus_set()
    sessions_win.wait_window(sessions_win)