# hourly_analysis_report.py

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import db_manager
import pytz
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import os
import matplotlib.font_manager as fm
import numpy as np

import arabic_reshaper
from bidi import algorithm as bidi

# تابع پردازش متن فارسی از فایل پیکربندی ایمپورت شده است
from matplotlib_persian_config import process_persian_text_for_matplotlib # فرض بر این است که این فایل وجود دارد

# -----------------------------------------------------------------------------
# تغییرات معماری:
# - حذف OPEN_TOPLEVEL_WINDOWS از این ماژول (فقط در app.py و settings_manager.py مدیریت می‌شود)
# - تابع show_hourly_analysis_report_window به گونه‌ای تغییر می‌کند که پنل‌های مختلف را بر اساس نیاز نمایش دهد.
# - UI کاملاً بازطراحی می‌شود.
# -----------------------------------------------------------------------------

# --- تنظیمات فونت فارسی برای Matplotlib (اگر از فایل جداگانه ایمپورت شده، این بخش تکراری نیست) ---
# این بخش فقط برای اجرای مستقل فایل در زمان توسعه است
# در اپلیکیشن اصلی، این تنظیمات باید توسط matplotlib_persian_config.py انجام شود.
FONT_NAME = None
persian_fonts_candidates = [
    "Vazirmatn", "IRANSans", "B Nazanin", "Nika", "Arial"
]

for font_candidate in persian_fonts_candidates:
    font_paths = fm.findfont(font_candidate)
    if font_paths:
        if isinstance(font_paths, list):
            if font_paths:
                FONT_NAME = font_candidate
                break
        else:
            FONT_NAME = font_candidate
            break

if FONT_NAME:
    plt.rcParams['font.family'] = FONT_NAME
    plt.rcParams['font.sans-serif'] = FONT_NAME
    plt.rcParams['axes.unicode_minus'] = False
else:
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
    plt.rcParams['axes.unicode_minus'] = False
# --- پایان تنظیمات فونت فارسی برای Matplotlib ---

# -----------------------------------------------------------------------------
# تعریف کلاس برای دکمه‌های فیلتر با استایل جدید (گوشه‌های گرد و رنگ سالید)
# -----------------------------------------------------------------------------
class RoundedButton(tk.Canvas):
    def __init__(self, parent, width, height, corner_radius, padding, color, text, font, command=None, text_color="white"):
        tk.Canvas.__init__(self, parent, width=width, height=height, bg=parent.cget('bg'), highlightthickness=0)
        self.width = width
        self.height = height
        self.corner_radius = corner_radius
        self.padding = padding
        self.color = color
        self.text = text
        self.font = font
        self.command = command
        self.text_color = text_color

        self.coords = self._round_rectangle_coords(0, 0, width, height, corner_radius)
        self.rect_id = self.create_polygon(self.coords, smooth=True, fill=self.color, outline="")
        self.text_id = self.create_text(width / 2, height / 2, text=process_persian_text_for_matplotlib(self.text), font=self.font, fill=self.text_color, justify='center')

        self.bind("<Button-1>", self._on_button_press)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        self.original_color = color
        self.darker_color = self._darken_color(color, 20) # 20% darke
        self.lighter_color = self._lighten_color(color, 20) # 20% lighter for checkboxes

    def _round_rectangle_coords(self, x1, y1, x2, y2, radius):
        points = [x1 + radius, y1,
                  x2 - radius, y1,
                  x2, y1 + radius,
                  x2, y2 - radius,
                  x2 - radius, y2,
                  x1 + radius, y2,
                  x1, y2 - radius,
                  x1, y1 + radius]
        return points

    def _darken_color(self, hex_color, factor):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darker_rgb = tuple(max(0, c - int(c * factor / 100)) for c in rgb)
        return '#%02x%02x%02x' % darker_rgb

    def _lighten_color(self, hex_color, factor):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        lighter_rgb = tuple(min(255, c + int((255 - c) * factor / 100)) for c in rgb)
        return '#%02x%02x%02x' % lighter_rgb

    def _on_button_press(self, event):
        self.itemconfig(self.rect_id, fill=self.darker_color)
        if self.command:
            self.after(100, self.command) # Short delay for visual feedback

    def _on_enter(self, event):
        self.itemconfig(self.rect_id, fill=self.darker_color)

    def _on_leave(self, event):
        self.itemconfig(self.rect_id, fill=self.original_color)

# -----------------------------------------------------------------------------
# تعریف تابع اصلی نمایش پنجره گزارش
# -----------------------------------------------------------------------------
def show_hourly_analysis_report_window(parent_root, open_toplevel_windows_list):
    report_win = tk.Toplevel(parent_root)
    report_win.title(process_persian_text_for_matplotlib("گزارش آنالیز ساعتی تریدها"))
    report_win.transient(parent_root)
    report_win.grab_set()
    report_win.resizable(True, True)

    # اضافه کردن پنجره به لیست مدیریت شده
    open_toplevel_windows_list.append(report_win)

    def on_report_win_close():
        if report_win in open_toplevel_windows_list:
            open_toplevel_windows_list.remove(report_win)
        report_win.destroy()

    report_win.protocol("WM_DELETE_WINDOW", on_report_win_close)

    screen_width = report_win.winfo_screenwidth()
    screen_height = report_win.winfo_screenheight()

    win_width = int(screen_width * 0.9)
    win_height = int(screen_height * 0.8)

    x = (screen_width / 2) - (win_width / 2)
    y = (screen_height / 2) - (win_height / 2)

    report_win.geometry(f'{win_width}x{win_height}+{int(x)}+{int(y)}')
    report_win.configure(bg="#F0F2F5")

    # -------------------------------------------------------------------------
    # بخش دکمه‌های اصلی فیلتر (بالای فرم)
    # -------------------------------------------------------------------------
    button_bar_frame = tk.Frame(report_win, bg="#F0F2F5", pady=10)
    button_bar_frame.pack(fill=tk.X, padx=20, pady=(15, 5))

    button_bar_frame.grid_columnconfigure(0, weight=1)
    button_bar_frame.grid_columnconfigure(1, weight=1)
    button_bar_frame.grid_columnconfigure(2, weight=1)
    button_bar_frame.grid_columnconfigure(3, weight=1)
    button_bar_frame.grid_columnconfigure(4, weight=1)

    button_width = 150
    button_height = 50
    button_corner_radius = 20
    button_font = ("Vazirmatn Regular", 10, "bold") # <<< استفاده از Vazirmatn-Regular

    # رنگ‌های پیشنهادی برای دکمه‌ها (میتونی بعداً تغییرشون بدی)
    color1 = "#4CAF50" # سبز
    color2 = "#2196F3" # آبی
    color3 = "#FFC107" # زرد/نارنجی
    color4 = "#9C27B0" # بنفش
    color5 = "#F44336" # قرمز (برای اعمال فیلترها)

    # دکمه 1: روزهای هفته
    btn_weekdays = RoundedButton(button_bar_frame, button_width, button_height, button_corner_radius, 5, color1,
                                 "روزهای هفته", button_font, command=lambda: show_filter_options("weekdays"))
    btn_weekdays.grid(row=0, column=4, padx=5) # RTL: از راست به چپ

    # دکمه 2: ساعات روز
    btn_hours = RoundedButton(button_bar_frame, button_width, button_height, button_corner_radius, 5, color2,
                              "ساعات روز", button_font, command=lambda: show_filter_options("hours"))
    btn_hours.grid(row=0, column=3, padx=5) # RTL: از راست به چپ

    # دکمه 3: نوع ترید
    btn_trade_type = RoundedButton(button_bar_frame, button_width, button_height, button_corner_radius, 5, color3,
                                  "نوع ترید", button_font, command=lambda: show_filter_options("trade_type"))
    btn_trade_type.grid(row=0, column=2, padx=5) # RTL: از راست به چپ

    # دکمه 4: لیست اشتباهات
    btn_errors = RoundedButton(button_bar_frame, button_width, button_height, button_corner_radius, 5, color4,
                               "لیست اشتباهات", button_font, command=lambda: show_filter_options("errors"))
    btn_errors.grid(row=0, column=1, padx=5) # RTL: از راست به چپ

    # دکمه 5: اعمال فیلترها (این دکمه کمی متفاوت عمل می‌کند)
    btn_apply_filters = RoundedButton(button_bar_frame, button_width + 20, button_height, button_corner_radius, 5, color5,
                                      "اعمال فیلترها", button_font, command=lambda: update_report_data())
    btn_apply_filters.grid(row=0, column=0, padx=5) # RTL: از راست به چپ (آخرین دکمه در این ردیف)

    # -------------------------------------------------------------------------
    # مستطیل باریک برای نمایش چک‌باکس‌ها
    # -------------------------------------------------------------------------
    filter_options_frame = tk.Frame(report_win, bg="#E0E0E0", height=60, padx=10, pady=5) # رنگ روشن‌تر
    filter_options_frame.pack(fill=tk.X, padx=20, pady=5)
    filter_options_frame.pack_propagate(False) # جلوگیری از تغییر اندازه فریم

    filter_options_canvas = tk.Canvas(filter_options_frame, bg="#E0E0E0", highlightthickness=0)
    filter_options_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    filter_options_scrollbar = ttk.Scrollbar(filter_options_frame, orient="horizontal", command=filter_options_canvas.xview)
    filter_options_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

    scrollable_checkbox_frame = tk.Frame(filter_options_canvas, bg="#E0E0E0")
    filter_options_canvas.create_window((0, 0), window=scrollable_checkbox_frame, anchor="nw")
    filter_options_canvas.configure(xscrollcommand=filter_options_scrollbar.set)
    scrollable_checkbox_frame.bind("<Configure>", lambda e: filter_options_canvas.configure(scrollregion=filter_options_canvas.bbox("all")))

    # -------------------------------------------------------------------------
    # فریم اصلی برای چارت و فیلترهای انتخابی
    # -------------------------------------------------------------------------
    main_content_frame = tk.Frame(report_win, bg="#F0F2F5", padx=20, pady=10)
    main_content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    main_content_frame.grid_columnconfigure(0, weight=4) # وزن بیشتر برای چارت (سمت چپ)
    main_content_frame.grid_columnconfigure(1, weight=1) # وزن کمتر برای فیلترهای انتخابی (سمت راست)
    main_content_frame.grid_rowconfigure(0, weight=1)

    # پنل چارت (سمت چپ)
    chart_panel = tk.Frame(main_content_frame, bg="white", relief="flat", bd=0)
    chart_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    chart_panel.grid_rowconfigure(0, weight=1)
    chart_panel.grid_columnconfigure(0, weight=1)

    # پنل فیلترهای انتخابی (سمت راست)
    selected_filters_panel = tk.Frame(main_content_frame, bg="white", padx=15, pady=15, relief="flat", bd=0)
    selected_filters_panel.grid(row=0, column=1, sticky="nsew")
    selected_filters_panel.grid_rowconfigure(99, weight=1) # برای اینکه محتوا به سمت بالا بچسبد

    tk.Label(selected_filters_panel, text=process_persian_text_for_matplotlib("فیلترهای انتخابی شما:"),
             font=("Segoe UI", 12, "bold"), bg="white", fg="#202124", justify='right').pack(pady=(0, 10), anchor='e')

    selected_filters_text = tk.Text(selected_filters_panel, wrap="word", height=10, bg="white", fg="#424242",
                                    font=("Vazirmatn Regular", 10), relief="flat", bd=0)
    selected_filters_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    selected_filters_text.tag_configure("rtl", justify='right')
    selected_filters_text.insert(tk.END, process_persian_text_for_matplotlib("هنوز فیلتری انتخاب نشده است."), "rtl")
    selected_filters_text.config(state=tk.DISABLED) # فقط خواندنی

    # -------------------------------------------------------------------------
    # متغیرها برای نگهداری فیلترهای انتخاب شده
    # -------------------------------------------------------------------------
    selected_weekdays_vars = {} # 0=Monday, 6=Sunday (Python's weekday)
    selected_hours_vars = {} # 0-23
    selected_trade_type_var = tk.StringVar(value="همه") # "Profit", "Loss", "RF", "همه"
    selected_errors_vars = {} # Original error names

    # دیکشنری برای نگهداری مقادیر فعلی که برای نمایش در selected_filters_panel استفاده می‌شود
    current_selected_filters_display = {
        "weekdays": [],
        "hours": [],
        "trade_type": "همه",
        "errors": []
    }
    
    # -------------------------------------------------------------------------
    # توابع برای نمایش گزینه‌های فیلتر (در مستطیل باریک)
    # -------------------------------------------------------------------------
    def clear_filter_options_frame():
        for widget in scrollable_checkbox_frame.winfo_children():
            widget.destroy()
        filter_options_canvas.xview_moveto(0) # اسکرول به ابتدا

    def update_selected_filters_display():
        selected_filters_text.config(state=tk.NORMAL)
        selected_filters_text.delete(1.0, tk.END)

        display_lines = []
        # تاریخ (همیشه نمایش داده شود)
        start_date_str = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d') # فعلاً ثابت، بعداً فیلتر اضافه می‌کنیم
        end_date_str = datetime.now().strftime('%Y-%m-%d') # فعلاً ثابت
        display_lines.append(f"بازه تاریخی: از {start_date_str} تا {end_date_str}")

        # روزهای هفته
        if current_selected_filters_display["weekdays"]:
            persian_weekday_names = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]
            selected_names = [persian_weekday_names[d] for d in current_selected_filters_display["weekdays"]]
            display_lines.append(f"روزهای هفته: {', '.join(selected_names)}")
        else:
            display_lines.append("روزهای هفته: همه")

        # ساعات روز
        if current_selected_filters_display["hours"]:
            display_lines.append(f"ساعات روز: {', '.join(map(str, sorted(current_selected_filters_display['hours'])))}")
        else:
            display_lines.append("ساعات روز: همه")

        # نوع ترید
        trade_type_map = {
            "Profit": "سودده", "Loss": "زیان‌ده", "RF": "ریسک‌فری", "همه": "همه"
        }
        display_lines.append(f"نوع ترید: {trade_type_map.get(current_selected_filters_display['trade_type'], 'همه')}")

        # لیست اشتباهات
        if current_selected_filters_display["errors"]:
            display_lines.append(f"لیست اشتباهات: {', '.join(current_selected_filters_display['errors'])}")
        else:
            display_lines.append("لیست اشتباهات: همه")

        for line in display_lines:
            selected_filters_text.insert(tk.END, process_persian_text_for_matplotlib(line) + "\n", "rtl")

        selected_filters_text.config(state=tk.DISABLED)


    def show_filter_options(filter_type):
        clear_filter_options_frame()

        def create_checkbox(parent_frame, text, var, cmd, bg_color):
            chk_frame = tk.Frame(parent_frame, bg=bg_color, relief="solid", bd=1)
            chk = tk.Checkbutton(chk_frame, text=process_persian_text_for_matplotlib(text), variable=var,
                                 command=cmd, bg=bg_color, font=("Vazirmatn Regular", 9),
                                 activebackground=bg_color, fg="#333333", selectcolor=bg_color)
            chk.pack(padx=5, pady=2, fill=tk.BOTH, expand=True) # Checkbutton fill the frame
            chk_frame.pack(side=tk.RIGHT, padx=5, pady=5) # Pack frames from right to left (RTL)

        def update_selection(filter_category, value, var):
            if filter_category == "trade_type":
                current_selected_filters_display[filter_category] = value
            elif var.get(): # Checkbox selected
                if value not in current_selected_filters_display[filter_category]:
                    current_selected_filters_display[filter_category].append(value)
            else: # Checkbox deselected
                if value in current_selected_filters_display[filter_category]:
                    current_selected_filters_display[filter_category].remove(value)
            update_selected_filters_display()


        if filter_type == "weekdays":
            # 0=Monday, 1=Tuesday, ..., 6=Sunday (Python's datetime.weekday())
            weekday_names = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]
            for i, name in enumerate(weekday_names):
                if i not in selected_weekdays_vars:
                    selected_weekdays_vars[i] = tk.BooleanVar(value=True) # Default all selected
                
                # Check if it was previously selected in display model
                if not current_selected_filters_display["weekdays"]: # If display list is empty, it means "All" is active
                     selected_weekdays_vars[i].set(True)
                elif i in current_selected_filters_display["weekdays"]:
                    selected_weekdays_vars[i].set(True)
                else:
                    selected_weekdays_vars[i].set(False)

                create_checkbox(scrollable_checkbox_frame, name, selected_weekdays_vars[i],
                                lambda idx=i, var=selected_weekdays_vars[i]: update_selection("weekdays", idx, var),
                                btn_weekdays.lighter_color)
            
            # Initial update for weekdays display
            if not current_selected_filters_display["weekdays"]: # If not set explicitly, default to all
                current_selected_filters_display["weekdays"] = list(range(7))
            update_selected_filters_display()

        elif filter_type == "hours":
            for i in range(24):
                if i not in selected_hours_vars:
                    selected_hours_vars[i] = tk.BooleanVar(value=True) # Default all selected
                
                # Check if it was previously selected in display model
                if not current_selected_filters_display["hours"]: # If display list is empty, it means "All" is active
                    selected_hours_vars[i].set(True)
                elif i in current_selected_filters_display["hours"]:
                    selected_hours_vars[i].set(True)
                else:
                    selected_hours_vars[i].set(False)

                create_checkbox(scrollable_checkbox_frame, f"{i:02d}:00", selected_hours_vars[i],
                                lambda idx=i, var=selected_hours_vars[i]: update_selection("hours", idx, var),
                                btn_hours.lighter_color)
            
            # Initial update for hours display
            if not current_selected_filters_display["hours"]:
                current_selected_filters_display["hours"] = list(range(24))
            update_selected_filters_display()

        elif filter_type == "trade_type":
            trade_types = ["همه", "Profit", "Loss", "RF"]
            # برای دکمه‌های رادیویی، فقط یکی میتونه انتخاب بشه، پس نیازی به لیست نیست
            # اما برای نمایش، باید مقدار انتخاب شده رو در current_selected_filters_display نگه داریم
            for t_type_raw in trade_types:
                t_type_display = process_persian_text_for_matplotlib(t_type_raw)
                radio_btn = tk.Radiobutton(scrollable_checkbox_frame, text=t_type_display,
                                            variable=selected_trade_type_var, value=t_type_raw,
                                            bg=btn_trade_type.lighter_color,
                                            command=lambda tt=t_type_raw: update_selection("trade_type", tt, None), # var=None for radio
                                            font=("Vazirmatn Regular", 9),
                                            activebackground=btn_trade_type.lighter_color,
                                            selectcolor=btn_trade_type.lighter_color)
                radio_btn.pack(side=tk.RIGHT, padx=5, pady=5) # RTL: از راست به چپ
            
            # مطمئن میشیم که حالت قبلی انتخاب شده دوباره تنظیم بشه
            selected_trade_type_var.set(current_selected_filters_display["trade_type"])
            update_selected_filters_display()

        elif filter_type == "errors":
            all_errors_from_db = db_manager.get_all_errors()
            for error_name in all_errors_from_db:
                if error_name not in selected_errors_vars:
                    selected_errors_vars[error_name] = tk.BooleanVar(value=True) # Default all selected
                
                # Check if it was previously selected in display model
                if not current_selected_filters_display["errors"]: # If display list is empty, it means "All" is active
                    selected_errors_vars[error_name].set(True)
                elif error_name in current_selected_filters_display["errors"]:
                    selected_errors_vars[error_name].set(True)
                else:
                    selected_errors_vars[error_name].set(False)

                create_checkbox(scrollable_checkbox_frame, error_name, selected_errors_vars[error_name],
                                lambda err=error_name, var=selected_errors_vars[error_name]: update_selection("errors", err, var),
                                btn_errors.lighter_color)
            
            # Initial update for errors display
            if not current_selected_filters_display["errors"]: # If not set explicitly, default to all
                current_selected_filters_display["errors"] = [err for err in all_errors_from_db]
            update_selected_filters_display()

    # -------------------------------------------------------------------------
    # توابع نمودار و آمار (مثل قبل، با تغییرات جزئی برای فونت و RTL)
    # -------------------------------------------------------------------------
    fig_line, ax_line = plt.subplots(figsize=(6, 4), dpi=100)
    canvas_line = FigureCanvasTkAgg(fig_line, master=chart_panel)
    canvas_widget_line = canvas_line.get_tk_widget()
    canvas_widget_line.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    fig_pie, ax_pie = plt.subplots(figsize=(6, 6), dpi=100)
    canvas_pie = FigureCanvasTkAgg(fig_pie, master=chart_panel) # فعلاً در همین پنل، بعداً تصمیم می‌گیریم
    # canvas_widget_pie = canvas_pie.get_tk_widget()
    # canvas_widget_pie.pack(fill=tk.BOTH, expand=True, padx=5, pady=5) # فعلاً نمایش داده نمی‌شود

    def update_line_chart(hourly_data, total_trades_in_range):
        ax_line.clear()

        hours = list(range(24))
        # این داده‌ها بر اساس ساعات نمایش در منطقه زمانی کاربر هستند
        profit_counts = [hourly_data.get(h, {}).get('Profit', 0) for h in hours]
        loss_counts = [hourly_data.get(h, {}).get('Loss', 0) for h in hours]
        rf_counts = [hourly_data.get(h, {}).get('RF', 0) for h in hours]

        if total_trades_in_range == 0:
            ax_line.text(0.5, 0.5, process_persian_text_for_matplotlib("داده‌ای برای نمایش نمودار وجود ندارد."),
                         horizontalalignment='center', verticalalignment='center', transform=ax_line.transAxes,
                         fontsize=10, color='gray', fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0]))
            ax_line.set_xticks([])
            ax_line.set_yticks([])
            canvas_line.draw()
            return

        bar_width = 0.8
        ax_line.bar(hours, profit_counts, bar_width, label=process_persian_text_for_matplotlib('سودده'), color='#66BB6A')
        ax_line.bar(hours, loss_counts, bar_width, bottom=profit_counts, label=process_persian_text_for_matplotlib('زیان‌ده'), color='#EF5350')
        ax_line.bar(hours, rf_counts, bar_width, bottom=[profit_counts[i] + loss_counts[i] for i in range(24)], label=process_persian_text_for_matplotlib('ریسک‌فری'), color='#42A5F5')

        ax_line.set_title(process_persian_text_for_matplotlib('تعداد تریدها بر اساس ساعت روز'), fontsize=12, fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0]))
        ax_line.set_xlabel(process_persian_text_for_matplotlib('ساعت (به وقت محلی)'), fontsize=10, fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0]))
        ax_line.set_ylabel(process_persian_text_for_matplotlib('تعداد تریدها'), fontsize=10, fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0]))

        ax_line.set_xticks(hours[::2])
        ax_line.set_xlim(-1, 24)

        ax_line.legend(loc='upper right', prop=fm.FontProperties(family=plt.rcParams['font.family'][0]))
        ax_line.grid(True, linestyle='--', alpha=0.6, axis='y')

        for i, total in enumerate([profit_counts[j] + loss_counts[j] + rf_counts[j] for j in range(24)]):
            if total > 0:
                ax_line.text(hours[i], total + 0.5, str(total), ha='center', va='bottom', fontsize=8, fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0]))

        fig_line.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
        canvas_line.draw()

    def update_pie_chart(error_counts):
        # این تابع فعلاً فعال نیست، اما نگه می‌داریم تا بعداً تصمیم بگیریم کجا نمایش داده شود
        ax_pie.clear()

        labels_raw = []
        sizes = []
        sorted_error_counts = sorted(error_counts.items(), key=lambda item: item[1], reverse=True)

        other_count = 0
        display_limit = 5

        for i, (error, count) in enumerate(sorted_error_counts):
            if i < display_limit:
                labels_raw.append(f"{error}")
                sizes.append(count)
            else:
                other_count += count

        if other_count > 0:
            labels_raw.append("متفرقه")
            sizes.append(other_count)

        if not sizes:
            ax_pie.text(0.5, 0.5, process_persian_text_for_matplotlib("داده‌ای برای نمایش نمودار دایره‌ای وجود ندارد."),
                        horizontalalignment='center', verticalalignment='center', transform=ax_pie.transAxes,
                        fontsize=10, color='gray', fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0]))
            ax_pie.set_xticks([])
            ax_pie.set_yticks([])
            canvas_pie.draw()
            return

        processed_labels_for_pie = [process_persian_text_for_matplotlib(label) for label in labels_raw]
        processed_labels_for_legend = [process_persian_text_for_matplotlib(f"{l_raw} ({s})") for l_raw, s in zip(labels_raw, sizes)]

        num_colors = len(processed_labels_for_pie)
        if num_colors <= 10:
            colors = plt.cm.get_cmap('tab10')(range(num_colors))
        elif num_colors <= 20:
            colors = plt.cm.get_cmap('tab20')(range(num_colors))
        else:
            colors = plt.cm.get_cmap('viridis')(np.linspace(0, 1, num_colors))

        wedges, texts, autotexts = ax_pie.pie(sizes, autopct='%1.1f%%', startangle=90,
                                              textprops={'fontsize': 8, 'fontproperties': fm.FontProperties(family=plt.rcParams['font.family'][0])},
                                              colors=colors, pctdistance=0.85, labels=processed_labels_for_pie)
        ax_pie.axis('equal')

        ax_pie.set_title(process_persian_text_for_matplotlib('توزیع خطاهای منتخب'), fontsize=12, fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0]))

        ax_pie.legend(wedges, processed_labels_for_legend,
                     title=process_persian_text_for_matplotlib("خطاها"),
                     loc="center left",
                     bbox_to_anchor=(1, 0, 0.5, 1),
                     prop=fm.FontProperties(family=plt.rcParams['font.family'][0]))

        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(9)
            autotext.set_weight('bold')
            autotext.set_fontproperties(fm.FontProperties(family=plt.rcParams['font.family'][0]))

        fig_pie.subplots_adjust(left=0.1, right=0.7, top=0.9, bottom=0.1)
        canvas_pie.draw()

    # -------------------------------------------------------------------------
    # تابع اصلی برای به‌روزرسانی گزارش بر اساس فیلترها (دکمه اعمال فیلترها)
    # -------------------------------------------------------------------------
    def update_report_data():
        # دریافت فیلترهای انتخابی از current_selected_filters_display
        selected_weekdays = current_selected_filters_display["weekdays"]
        selected_hours = current_selected_filters_display["hours"]
        selected_trade_type = current_selected_filters_display["trade_type"]
        selected_errors_filter = current_selected_filters_display["errors"] # اینها صرفاً برای نمایش و فیلتر چارت استفاده میشن

        # فعلاً تاریخ رو ثابت می‌گیریم تا بعداً بهش فیلتر اضافه کنیم
        start_date_str = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date_str = datetime.now().strftime('%Y-%m-%d')

        all_relevant_trades = db_manager.get_trades_for_hourly_analysis(
            start_date_str, end_date_str, selected_trade_type
        )

        filtered_trades_for_analysis = []
        current_display_timezone = pytz.timezone(db_manager.get_default_timezone())

        for trade in all_relevant_trades:
            # فیلتر کردن بر اساس روزهای هفته
            try:
                utc_naive_dt = datetime.strptime(f"{trade['date']} {trade['time']}", "%Y-%m-%d %H:%M")
                utc_aware_dt = pytz.utc.localize(utc_naive_dt)
                display_aware_dt = utc_aware_dt.astimezone(current_display_timezone)
                
                weekday_in_display_tz = display_aware_dt.weekday() # 0=Monday, 6=Sunday
                hour_in_display_tz = display_aware_dt.hour

                if selected_weekdays and weekday_in_display_tz not in selected_weekdays:
                    continue
                if selected_hours and hour_in_display_tz not in selected_hours:
                    continue

                # فیلتر کردن بر اساس خطاها (اگر فیلتری اعمال شده باشد)
                if selected_errors_filter:
                    trade_errors_list = [e.strip() for e in trade['errors'].split(',') if e.strip()]
                    if not any(err_filter in trade_errors_list for err_filter in selected_errors_filter):
                        continue
                
                filtered_trades_for_analysis.append(trade)

            except Exception as e:
                print(f"Error processing trade {trade.get('id')}: {e}")
                continue

        hourly_profit_loss_rf_counts = defaultdict(lambda: Counter())
        all_filtered_errors_for_pie = []

        total_trades_count = len(filtered_trades_for_analysis)
        profit_count = 0
        loss_count = 0
        rf_count = 0

        for trade in filtered_trades_for_analysis:
            try:
                utc_naive_dt = datetime.strptime(f"{trade['date']} {trade['time']}", "%Y-%m-%d %H:%M")
                utc_aware_dt = pytz.utc.localize(utc_naive_dt)
                display_aware_dt = utc_aware_dt.astimezone(current_display_timezone)

                hour_in_display_tz = display_aware_dt.hour

                hourly_profit_loss_rf_counts[hour_in_display_tz][trade['profit']] += 1

                if trade['profit'] == 'Profit':
                    profit_count += 1
                elif trade['profit'] == 'Loss':
                    loss_count += 1
                elif trade['profit'] == 'RF':
                    rf_count += 1

                # اینجا فقط خطاهایی رو جمع‌آوری می‌کنیم که از فیلتر selected_errors_filter عبور کرده باشند
                if trade['errors']:
                    trade_errors_list = [e.strip() for e in trade['errors'].split(',') if e.strip()]
                    for err in trade_errors_list:
                        # اگر فیلتری برای خطاها انتخاب نشده باشد، همه را اضافه کن
                        # یا اگر انتخاب شده و این خطا جزو انتخاب شده‌ها باشد، اضافه کن
                        if not selected_errors_filter or err in selected_errors_filter:
                            all_filtered_errors_for_pie.append(err)

            except Exception as e:
                print(f"Error processing trade {trade.get('id')}: {e}")
                continue

        error_frequency_counts = Counter(all_filtered_errors_for_pie)

        update_line_chart(hourly_profit_loss_rf_counts, total_trades_count)
        # update_pie_chart(error_frequency_counts) # فعلاً غیرفعال

    # اولین بار که پنجره باز می‌شود، فیلترهای پیش‌فرض را نمایش دهد
    show_filter_options("weekdays") # ابتدا گزینه‌های روزهای هفته را نمایش دهد
    update_report_data() # اولین بار گزارش را با فیلترهای پیش‌فرض بارگذاری کن

    report_win.focus_set()
    report_win.wait_window(report_win)

# برای تست مستقل (فقط برای توسعه)
if __name__ == "__main__":
    class MockDBManager:
        def get_default_timezone(self):
            return 'Asia/Tehran'

        def get_all_errors(self):
            return ["ورود زودهنگام", "Overtrading", "نقض قوانین", "بدون برنامه", "احساساتی", "حرکات ناگهانی", "عدم مدیریت ریسک", "روانشناسی", "مدیریت سرمایه", "انتظار بیجا", "ریسک به ریوارد نامناسب"]

        def get_trades_for_hourly_analysis(self, start_date_str, end_date_str, trade_type_filter):
            mock_trades = [
                {'id': 1, 'date': '2025-07-14', 'time': '02:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'},
                {'id': 2, 'date': '2025-07-14', 'time': '05:00', 'profit': 'Loss', 'errors': 'Overtrading, نقض قوانین', 'original_timezone': 'UTC'},
                {'id': 3, 'date': '2025-07-14', 'time': '08:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'},
                {'id': 4, 'date': '2025-07-14', 'time': '10:00', 'profit': 'RF', 'errors': 'بدون برنامه', 'original_timezone': 'UTC'},
                {'id': 5, 'date': '2025-07-14', 'time': '13:00', 'profit': 'Loss', 'errors': 'ورود زودهنگام, احساساتی', 'original_timezone': 'UTC'},
                {'id': 6, 'date': '2025-07-14', 'time': '16:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'},
                {'id': 7, 'date': '2025-07-14', 'time': '19:00', 'profit': 'Loss', 'errors': 'Overtrading', 'original_timezone': 'UTC'},
                {'id': 8, 'date': '2025-07-14', 'time': '22:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'},

                {'id': 9, 'date': '2025-07-15', 'time': '03:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'},
                {'id': 10, 'date': '2025-07-15', 'time': '06:00', 'profit': 'Loss', 'errors': 'نقض قوانین, حرکات ناگهانی', 'original_timezone': 'UTC'},
                {'id': 11, 'date': '2025-07-15', 'time': '09:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'},
                {'id': 12, 'date': '2025-07-15', 'time': '11:00', 'profit': 'RF', 'errors': 'بدون برنامه', 'original_timezone': 'UTC'},
                {'id': 13, 'date': '2025-07-15', 'time': '14:00', 'profit': 'Loss', 'errors': 'ورود زودهنگام, عدم مدیریت ریسک', 'original_timezone': 'UTC'},
                {'id': 14, 'date': '2025-07-15', 'time': '17:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'},
                {'id': 15, 'date': '2025-07-15', 'time': '20:00', 'profit': 'Loss', 'errors': 'Overtrading', 'original_timezone': 'UTC'},

                {'id': 16, 'date': '2025-07-16', 'time': '07:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'},
                {'id': 17, 'date': '2025-07-16', 'time': '09:00', 'profit': 'Loss', 'errors': 'روانشناسی', 'original_timezone': 'UTC'},
                {'id': 18, 'date': '2025-07-16', 'time': '10:00', 'profit': 'RF', 'errors': 'مدیریت سرمایه', 'original_timezone': 'UTC'},
                {'id': 19, 'date': '2025-07-16', 'time': '13:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'},
                {'id': 20, 'date': '2025-07-16', 'time': '15:00', 'profit': 'Loss', 'errors': 'انتظار بیجا, ریسک به ریوارد نامناسب', 'original_timezone': 'UTC'},

                # تریدهای اضافی برای تست روزهای هفته
                {'id': 21, 'date': '2025-07-14', 'time': '01:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'}, # Monday (0)
                {'id': 22, 'date': '2025-07-15', 'time': '01:00', 'profit': 'Loss', 'errors': '', 'original_timezone': 'UTC'}, # Tuesday (1)
                {'id': 23, 'date': '2025-07-16', 'time': '01:00', 'profit': 'RF', 'errors': '', 'original_timezone': 'UTC'}, # Wednesday (2)
                {'id': 24, 'date': '2025-07-17', 'time': '01:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'}, # Thursday (3)
                {'id': 25, 'date': '2025-07-18', 'time': '01:00', 'profit': 'Loss', 'errors': '', 'original_timezone': 'UTC'}, # Friday (4)
                {'id': 26, 'date': '2025-07-19', 'time': '01:00', 'profit': 'RF', 'errors': '', 'original_timezone': 'UTC'}, # Saturday (5)
                {'id': 27, 'date': '2025-07-20', 'time': '01:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'}, # Sunday (6)
            ]

            filtered_by_date = []
            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            for trade in mock_trades:
                trade_date = datetime.strptime(trade['date'], "%Y-%m-%d").date()
                if start_dt <= trade_date <= end_dt:
                    if trade_type_filter == "همه" or trade['profit'] == trade_type_filter:
                        filtered_by_date.append(trade)

            return filtered_by_date

    db_manager = MockDBManager()

    root_test = tk.Tk()
    root_test.withdraw()

    mock_open_windows = []
    show_hourly_analysis_report_window(root_test, mock_open_windows)
    root_test.mainloop()