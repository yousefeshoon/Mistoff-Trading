# hourly_analysis_report.py

import customtkinter as ctk
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
from matplotlib_persian_config import process_persian_text_for_matplotlib

# -----------------------------------------------------------------------------
# تنظیمات CTk
# -----------------------------------------------------------------------------
ctk.set_appearance_mode("light")  # یا "Dark" یا "System"
ctk.set_default_color_theme("blue") # یا "green" یا "dark-blue"

# --- تنظیمات فونت فارسی برای Matplotlib (اگر از فایل جداگانه ایمپورت شده، این بخش تکراری نیست) ---
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

# -------------------------------------------------------------------------
# توابع کمکی برای رنگ
# -------------------------------------------------------------------------
def _darken_color(hex_color, factor):
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    darker_rgb = tuple(max(0, c - int(c * factor / 100)) for c in rgb)
    return '#%02x%02x%02x' % darker_rgb

def _lighten_color(hex_color, factor):
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    lighter_rgb = tuple(min(255, c + int((255 - c) * factor / 100)) for c in rgb)
    return '#%02x%02x%02x' % lighter_rgb

# -----------------------------------------------------------------------------
# تابع اصلی نمایش پنجره گزارش
# -----------------------------------------------------------------------------
def show_hourly_analysis_report_window(parent_root, open_toplevel_windows_list):
    report_win = ctk.CTkToplevel(parent_root)
    report_win.title(process_persian_text_for_matplotlib("گزارش آنالیز ساعتی تریدها"))
    report_win.transient(parent_root)
    report_win.grab_set()
    report_win.resizable(True, True)

    # اضافه کردن پنجره به لیست مدیریت شده
    open_toplevel_windows_list.append(report_win)

    # Dictionary to store trace IDs for later removal
    # trace_ids رو به این صورت برای هر متغیر CTkVar نگه می‌داریم تا بتونیم دقیقاً اون trace رو پاک کنیم
    trace_ids = {
        'selected_trade_type_var': [], # برای StringVar
        'all_weekdays_var': [], # برای BooleanVar های "همه"
        'all_hours_var': [],
        'all_errors_var': [],
        'individual_vars': {} # برای BooleanVar های فردی (کلید: id(var_obj), مقدار: [trace_id1, trace_id2])
    }

    def on_report_win_close():
        # Remove all traces before destroying widgets to prevent errors
        # پاک کردن trace برای selected_trade_type_var
        for trace_id in trace_ids['selected_trade_type_var']:
            selected_trade_type_var.trace_vdelete("write", trace_id)
        
        # پاک کردن trace برای BooleanVar های "همه"
        for var_name in ['all_weekdays_var', 'all_hours_var', 'all_errors_var']:
            for trace_id in trace_ids[var_name]:
                if globals()[var_name].winfo_exists(): # مطمئن بشیم متغیر هنوز وجود داره
                     globals()[var_name].trace_vdelete("write", trace_id)

        # پاک کردن trace برای BooleanVar های فردی
        for var_obj_id, ids_list in trace_ids['individual_vars'].items():
            # از این طریق نمیتونیم به آبجکت اصلی BooleanVar دسترسی پیدا کنیم مگر اینکه دیکشنری selected_vars_dict رو اینجا هم داشته باشیم
            # بهترین راه اینه که موقع ساخت widget، خود widget رو به لیست trace_ids اضافه کنیم
            # و موقع destroy کردن، widget.destroy_traces() رو صدا بزنیم اگر CTk این قابلیت رو داشت
            # فعلا این رو به حالت قبل برمیگردونم و روی یک راه حل قویتر فکر میکنم.
            pass # این بخش رو فعلاً خالی میذارم تا ارور نده و به صورت اتوماتیک توسط CTk مدیریت بشه.


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
    report_win.configure(fg_color="#F0F2F5")

    # -------------------------------------------------------------------------
    # بخش دکمه‌های اصلی فیلتر (بالای فرم)
    # -------------------------------------------------------------------------
    button_bar_frame = ctk.CTkFrame(report_win, fg_color="#F0F2F5")
    button_bar_frame.pack(fill=tk.X, padx=20, pady=(15, 5))

    button_bar_frame.grid_columnconfigure(0, weight=1)
    button_bar_frame.grid_columnconfigure(1, weight=1)
    button_bar_frame.grid_columnconfigure(2, weight=1)
    button_bar_frame.grid_columnconfigure(3, weight=1)
    button_bar_frame.grid_columnconfigure(4, weight=1)
    button_bar_frame.grid_columnconfigure(5, weight=1)

    # سایز دکمه‌ها
    button_width = 150
    button_height = 50
    button_corner_radius = 12
    button_font = ("Vazirmatn Regular", 14, "bold")

    # رنگ‌های پیشنهادی برای دکمه‌ها
    color_date = "#FF9800"
    color1 = "#4CAF50"
    color2 = "#2196F3"
    color3 = "#FFC107"
    color4 = "#9C27B0"
    color5 = "#F44336"

    # دکمه "بازه تاریخی" (ستون 5 از راست) - دکمه اول
    btn_date_range = ctk.CTkButton(button_bar_frame, width=button_width, height=button_height,
                                   corner_radius=button_corner_radius,
                                   fg_color=color_date, text_color="white",
                                   text=process_persian_text_for_matplotlib("بازه تاریخی"),
                                   font=button_font,
                                   hover_color=_darken_color(color_date, 15),
                                   command=lambda: show_filter_options("date_range", color_date))
    btn_date_range.grid(row=0, column=5, padx=5)

    # دکمه روزهای هفته (ستون 4 از راست)
    btn_weekdays = ctk.CTkButton(button_bar_frame, width=button_width, height=button_height,
                                 corner_radius=button_corner_radius,
                                 fg_color=color1, text_color="white",
                                 text=process_persian_text_for_matplotlib("روزهای هفته"),
                                 font=button_font,
                                 hover_color=_darken_color(color1, 15),
                                 command=lambda: show_filter_options("weekdays", color1))
    btn_weekdays.grid(row=0, column=4, padx=5)

    # دکمه ساعات روز (ستون 3 از راست)
    btn_hours = ctk.CTkButton(button_bar_frame, width=button_width, height=button_height,
                              corner_radius=button_corner_radius,
                              fg_color=color2, text_color="white",
                              text=process_persian_text_for_matplotlib("ساعات روز"),
                              font=button_font,
                              hover_color=_darken_color(color2, 15),
                              command=lambda: show_filter_options("hours", color2))
    btn_hours.grid(row=0, column=3, padx=5)

    # دکمه نوع ترید (ستون 2 از راست)
    btn_trade_type = ctk.CTkButton(button_bar_frame, width=button_width, height=button_height,
                                  corner_radius=button_corner_radius,
                                  fg_color=color3, text_color="white",
                                  text=process_persian_text_for_matplotlib("نوع ترید"),
                                  font=button_font,
                                  hover_color=_darken_color(color3, 15),
                                  command=lambda: show_filter_options("trade_type", color3))
    btn_trade_type.grid(row=0, column=2, padx=5)

    # دکمه لیست اشتباهات (ستون 1 از راست)
    btn_errors = ctk.CTkButton(button_bar_frame, width=button_width, height=button_height,
                               corner_radius=button_corner_radius,
                               fg_color=color4, text_color="white",
                               text=process_persian_text_for_matplotlib("لیست اشتباهات"),
                               font=button_font,
                               hover_color=_darken_color(color4, 15),
                               command=lambda: show_filter_options("errors", color4))
    btn_errors.grid(row=0, column=1, padx=5)

    # دکمه اعمال فیلترها (ستون 0 از راست)
    btn_apply_filters = ctk.CTkButton(button_bar_frame, width=button_width + 20, height=button_height,
                                      corner_radius=button_corner_radius,
                                      fg_color=color5, text_color="white",
                                      text=process_persian_text_for_matplotlib("اعمال فیلترها"),
                                      font=button_font,
                                      hover_color=_darken_color(color5, 15),
                                      command=lambda: update_report_data())
    btn_apply_filters.grid(row=0, column=0, padx=5)

    # -------------------------------------------------------------------------
    # مستطیل باریک برای نمایش چک‌باکس‌ها
    # -------------------------------------------------------------------------
    filter_options_container = ctk.CTkFrame(report_win, fg_color="#E0E0E0", height=60, corner_radius=8)
    filter_options_container.pack(fill=tk.X, padx=20, pady=5)
    filter_options_container.pack_propagate(False)

    # فریم برای نگهداری دکمه "همه..." (فریز شده)
    all_option_frame = ctk.CTkFrame(filter_options_container, fg_color="transparent")
    all_option_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10))

    scrollable_checkbox_frame = ctk.CTkScrollableFrame(filter_options_container, orientation="horizontal",
                                                       fg_color="#E0E0E0",
                                                       scrollbar_button_color="#9E9E9E",
                                                       scrollbar_button_hover_color="#757575")
    scrollable_checkbox_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

    # -------------------------------------------------------------------------
    # فریم اصلی برای چارت و فیلترهای انتخابی
    # -------------------------------------------------------------------------
    main_content_frame = ctk.CTkFrame(report_win, fg_color="#F0F2F5")
    main_content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    main_content_frame.grid_columnconfigure(0, weight=4)
    main_content_frame.grid_columnconfigure(1, weight=1)
    main_content_frame.grid_rowconfigure(0, weight=1)

    # پنل چارت (سمت چپ)
    chart_panel = ctk.CTkFrame(main_content_frame, fg_color="white", corner_radius=8)
    chart_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    chart_panel.grid_rowconfigure(0, weight=1)
    chart_panel.grid_columnconfigure(0, weight=1)

    # پنل فیلترهای انتخابی (سمت راست)
    selected_filters_panel = ctk.CTkFrame(main_content_frame, fg_color="white", corner_radius=8)
    selected_filters_panel.grid(row=0, column=1, sticky="nsew")
    selected_filters_panel.grid_rowconfigure(99, weight=1)

    ctk.CTkLabel(selected_filters_panel, text=process_persian_text_for_matplotlib("فیلترهای انتخابی شما:"),
                 font=("Vazirmatn Regular", 12, "bold"), text_color="#202124", anchor='e', justify='right').pack(pady=(0, 10), padx=10, anchor='e')

    filters_table_frame = ctk.CTkFrame(selected_filters_panel, fg_color="white")
    filters_table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    filters_table_frame.grid_columnconfigure(0, weight=2) # ستون مقدار (چپ)
    filters_table_frame.grid_columnconfigure(1, weight=1) # ستون عنوان فیلتر (راست)

    header_font = ("Vazirmatn Regular", 10, "bold")
    value_font_normal = ("Vazirmatn Regular", 10)
    value_font_bold = ("Vazirmatn Regular", 10, "bold")

    ctk.CTkLabel(filters_table_frame, text=process_persian_text_for_matplotlib("عنوان فیلتر"),
                 font=header_font, text_color="#5F6368", anchor='e', justify='right').grid(row=0, column=1, sticky='ew', padx=2, pady=2)
    ctk.CTkLabel(filters_table_frame, text=process_persian_text_for_matplotlib("مقدار"),
                 font=header_font, text_color="#5F6368", anchor='e', justify='right').grid(row=0, column=0, sticky='ew', padx=2, pady=2)

    # -------------------------------------------------------------------------
    # متغیرها برای نگهداری فیلترهای انتخاب شده
    # -------------------------------------------------------------------------
    selected_date_range_vars = {
        "start_date": ctk.StringVar(value=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')),
        "end_date": ctk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
    }
    selected_weekdays_vars = {}
    selected_hours_vars = {}
    selected_trade_type_var = ctk.StringVar(value="همه")
    selected_errors_vars = {}

    current_selected_filters_display = {
        "date_range": {},
        "weekdays": [],
        "hours": [],
        "trade_type": "همه",
        "errors": []
    }

    all_weekdays_var = ctk.BooleanVar(value=True)
    all_hours_var = ctk.BooleanVar(value=True)
    all_errors_var = ctk.BooleanVar(value=True)


    # -------------------------------------------------------------------------
    # توابع برای نمایش گزینه‌های فیلتر (در مستطیل باریک)
    # -------------------------------------------------------------------------
    def clear_filter_options_frame():
        for widget in all_option_frame.winfo_children():
            widget.destroy()
        for widget in scrollable_checkbox_frame.winfo_children():
            widget.destroy()


    def update_selected_filters_display():
        # پاک کردن محتوای قبلی جدول
        for widget in filters_table_frame.winfo_children():
            if int(widget.grid_info()["row"]) > 0:
                widget.destroy()

        current_row = 1
        
        filter_data = []

        # بازه تاریخی
        start_date_str_display = current_selected_filters_display["date_range"].get("start_date", (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date_str_display = current_selected_filters_display["date_range"].get("end_date", datetime.now().strftime('%Y-%m-%d'))
        filter_data.append(("بازه تاریخی", f"از {process_persian_text_for_matplotlib(start_date_str_display)} تا {process_persian_text_for_matplotlib(end_date_str_display)}"))


        # روزهای هفته
        if current_selected_filters_display["weekdays"] and len(current_selected_filters_display["weekdays"]) < 7:
            persian_weekday_names = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]
            selected_names = [persian_weekday_names[d] for d in sorted(current_selected_filters_display["weekdays"])]
            filter_data.append(("روزهای هفته", ', '.join(selected_names)))
        else:
            filter_data.append(("روزهای هفته", "همه"))

        # ساعات روز
        if current_selected_filters_display["hours"] and len(current_selected_filters_display["hours"]) < 24:
            filter_data.append(("ساعات روز", ', '.join([f'{h:02d}:00' for h in sorted(current_selected_filters_display['hours'])]) ))
        else:
            filter_data.append(("ساعات روز", "همه"))

        # نوع ترید
        trade_type_map = {
            "Profit": "سودده", "Loss": "زیان‌ده", "RF": "ریسک‌فری", "همه": "همه"
        }
        filter_data.append(("نوع ترید", trade_type_map.get(current_selected_filters_display['trade_type'], 'همه')))

        # لیست اشتباهات
        all_db_errors = db_manager.get_all_errors()
        if current_selected_filters_display["errors"] and len(current_selected_filters_display["errors"]) < len(all_db_errors):
            filter_data.append(("لیست اشتباهات", ', '.join(current_selected_filters_display['errors'])))
        else:
            filter_data.append(("لیست اشتباهات", "همه"))

        # اضافه کردن سطرها به جدول
        for title, value in filter_data:
            ctk.CTkLabel(filters_table_frame, text=process_persian_text_for_matplotlib(f"{title}:"),
                         font=value_font_normal, text_color="#424242", anchor='e', justify='right').grid(row=current_row, column=1, sticky='ew', padx=2, pady=2)
            
            value_label = ctk.CTkLabel(filters_table_frame, text=process_persian_text_for_matplotlib(f"{value}"),
                         font=value_font_bold, text_color="#424242", anchor='e', justify='right',
                         wraplength=200) # مقدار پیشفرض اولیه
            value_label.grid(row=current_row, column=0, sticky='ew', padx=2, pady=2)
            
            current_row += 1

        def _on_table_resize(event=None):
            if not filters_table_frame.winfo_exists() or filters_table_frame.winfo_width() < 10:
                filters_table_frame.after(100, _on_table_resize)
                return

            new_wraplength = filters_table_frame.winfo_width() * 0.6 - 4
            
            for r in range(1, current_row):
                for child in filters_table_frame.grid_slaves(row=r, column=0):
                    if isinstance(child, ctk.CTkLabel):
                        child.configure(wraplength=new_wraplength)

        filters_table_frame.bind("<Configure>", _on_table_resize)
        _on_table_resize()
    
    def show_filter_options(filter_type, border_color):
        clear_filter_options_frame()

        def create_checkbox_or_radio(parent_frame, text, var, cmd, is_radio=False, is_all_option=False):
            chk_font = ("Vazirmatn Regular", 9, "bold") if is_all_option else ("Vazirmatn Regular", 9)
            
            selected_fg_color = border_color
            unselected_fg_color = filter_options_container.cget('fg_color')
            
            selected_text_color = "white" if is_all_option else "#333333"
            unselected_text_color = "#333333"

            if is_radio:
                widget = ctk.CTkRadioButton(parent_frame, text=process_persian_text_for_matplotlib(text),
                                            variable=var, value=text, command=cmd,
                                            fg_color=unselected_fg_color,
                                            hover_color=_lighten_color(border_color, 40),
                                            text_color=unselected_text_color,
                                            font=chk_font,
                                            corner_radius=8,
                                            radiobutton_width=16,
                                            radiobutton_height=16,
                                            border_width=2,
                                            border_color=border_color
                                            )
                # Store trace ID for selected_trade_type_var
                trace_id = var.trace_add("write", lambda *args: radio_select_callback(widget, var, text, selected_fg_color, selected_text_color, unselected_fg_color, unselected_text_color, chk_font, is_all_option))
                trace_ids['selected_trade_type_var'].append(trace_id)

                # تنظیم اولیه وضعیت
                if var.get() == text:
                    widget.configure(fg_color=selected_fg_color, text_color=selected_text_color)
                    widget.configure(font=("Vazirmatn Regular", 10, "bold") if is_all_option else ("Vazirmatn Regular", 10, "bold"))
                else:
                    widget.configure(fg_color=unselected_fg_color, text_color=unselected_text_color)
                    widget.configure(font=chk_font)

            else: # Checkbox
                widget = ctk.CTkCheckBox(parent_frame, text=process_persian_text_for_matplotlib(text),
                                         variable=var, command=cmd,
                                         fg_color=unselected_fg_color,
                                         hover_color=_lighten_color(border_color, 40),
                                         text_color=unselected_text_color,
                                         font=chk_font,
                                         corner_radius=8,
                                         checkbox_width=16,
                                         checkbox_height=16,
                                         border_width=2,
                                         border_color=border_color,
                                         checkmark_color="white"
                                         )
                # Store trace ID for individual and "all" checkboxes
                if id(var) not in trace_ids['individual_vars']:
                    trace_ids['individual_vars'][id(var)] = []
                trace_id = var.trace_add("write", lambda *args: chk_select_callback(widget, var, selected_fg_color, selected_text_color, unselected_fg_color, unselected_text_color, chk_font, is_all_option))
                trace_ids['individual_vars'][id(var)].append(trace_id) # Store by var's ID

                # تنظیم اولیه وضعیت
                if var.get():
                    widget.configure(fg_color=selected_fg_color, text_color=selected_text_color)
                    widget.configure(font=("Vazirmatn Regular", 10, "bold") if is_all_option else ("Vazirmatn Regular", 10, "bold"))
                else:
                    widget.configure(fg_color=unselected_fg_color, text_color=unselected_text_color)
                    widget.configure(font=chk_font)

            return widget
        
        # Define callbacks (moved outside create_checkbox_or_radio to avoid redefinition)
        def radio_select_callback(widget, var, text, selected_fg_color, selected_text_color, unselected_fg_color, unselected_text_color, chk_font, is_all_option):
            if widget.winfo_exists():
                if var.get() == text:
                    widget.configure(fg_color=selected_fg_color, text_color=selected_text_color)
                    widget.configure(font=("Vazirmatn Regular", 10, "bold") if is_all_option else ("Vazirmatn Regular", 10, "bold"))
                else:
                    widget.configure(fg_color=unselected_fg_color, text_color=unselected_text_color)
                    widget.configure(font=chk_font)

        def chk_select_callback(widget, var, selected_fg_color, selected_text_color, unselected_fg_color, unselected_text_color, chk_font, is_all_option):
            if widget.winfo_exists():
                if var.get():
                    widget.configure(fg_color=selected_fg_color, text_color=selected_text_color)
                    widget.configure(font=("Vazirmatn Regular", 10, "bold") if is_all_option else ("Vazirmatn Regular", 10, "bold"))
                else:
                    widget.configure(fg_color=unselected_fg_color, text_color=unselected_text_color)
                    widget.configure(font=chk_font)

        # این تابع وضعیت `selected_..._vars` را بر اساس `current_selected_filters_display` مقداردهی می‌کند
        # و همچنین وضعیت `all_..._var` را مدیریت می‌کند.
        def _set_individual_checkbox_states(filter_category, all_var_ref, selected_vars_dict, all_items_list):
            # اگر "همه" انتخاب شده بود، همه چک‌باکس‌های فردی رو فعال کن
            if all_var_ref.get():
                for item_key in all_items_list:
                    if item_key not in selected_vars_dict: # مطمئن بشیم متغیرش ساخته شده
                        selected_vars_dict[item_key] = ctk.BooleanVar()
                    selected_vars_dict[item_key].set(True)
            else: # اگر "همه" انتخاب نشده بود، وضعیت فردی رو از current_selected_filters_display بگیر
                for item_key in all_items_list:
                    if item_key not in selected_vars_dict:
                        selected_vars_dict[item_key] = ctk.BooleanVar()
                    if item_key in current_selected_filters_display[filter_category]:
                        selected_vars_dict[item_key].set(True)
                    else:
                        selected_vars_dict[item_key].set(False)

        def update_selection(filter_category, value, var):
            if filter_category == "date_range":
                start_date_str_val = selected_date_range_vars["start_date"].get()
                end_date_str_val = selected_date_range_vars["end_date"].get()
                
                try:
                    datetime.strptime(start_date_str_val, '%Y-%m-%d')
                    datetime.strptime(end_date_str_val, '%Y-%m-%d')
                    current_selected_filters_display["date_range"]["start_date"] = start_date_str_val
                    current_selected_filters_display["date_range"]["end_date"] = end_date_str_val
                except ValueError:
                    messagebox.showwarning(process_persian_text_for_matplotlib("خطا در تاریخ"), process_persian_text_for_matplotlib("فرمت تاریخ نامعتبر است. لطفاً از فرمت YYYY-MM-DD استفاده کنید."))
                    selected_date_range_vars["start_date"].set(current_selected_filters_display["date_range"].get("start_date", (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')))
                    selected_date_range_vars["end_date"].set(current_selected_filters_display["date_range"].get("end_date", datetime.now().strftime('%Y-%m-%d')))
                    return

            elif filter_category == "trade_type":
                current_selected_filters_display[filter_category] = value
            elif value in ["همه روزها", "همه ساعات", "همه خطاها"]:
                if filter_category == "weekdays":
                    all_items = list(range(7))
                    target_vars = selected_weekdays_vars
                    all_var_ref = all_weekdays_var
                elif filter_category == "hours":
                    all_items = list(range(24))
                    target_vars = selected_hours_vars
                    all_var_ref = all_hours_var
                elif filter_category == "errors":
                    all_items = db_manager.get_all_errors()
                    target_vars = selected_errors_vars
                    all_var_ref = all_errors_var
                
                if var.get(): # "همه" انتخاب شد
                    for item_key in all_items:
                        if item_key not in target_vars: # اگر متغیرش هنوز ساخته نشده، بسازش
                            target_vars[item_key] = ctk.BooleanVar()
                        target_vars[item_key].set(True)
                    current_selected_filters_display[filter_category] = all_items
                else: # "همه" غیرفعال شد
                    for item_key in all_items:
                        if item_key in target_vars: # فقط اگر متغیر وجود داشت
                            target_vars[item_key].set(False)
                    current_selected_filters_display[filter_category] = []
            else: # چک باکس‌های فردی
                if var.get(): # فعال شد
                    if value not in current_selected_filters_display[filter_category]:
                        current_selected_filters_display[filter_category].append(value)
                    
                    # اگر "همه" فعال بود، حالا غیرفعالش کن
                    if filter_category == "weekdays" and all_weekdays_var.get():
                         all_weekdays_var.set(False)
                    elif filter_category == "hours" and all_hours_var.get():
                         all_hours_var.set(False)
                    elif filter_category == "errors" and all_errors_var.get():
                         all_errors_var.set(False)
                else: # غیرفعال شد
                    if value in current_selected_filters_display[filter_category]:
                        current_selected_filters_display[filter_category].remove(value)
                    
                    # اگر همه چک باکس‌های فردی دیگه فعال نیستن، "همه" رو فعال کن
                    if filter_category == "weekdays":
                        if not any(selected_weekdays_vars[k].get() for k in selected_weekdays_vars if k != "همه روزها") and not all_weekdays_var.get():
                            all_weekdays_var.set(True)
                    elif filter_category == "hours":
                        if not any(selected_hours_vars[k].get() for k in selected_hours_vars if k != "همه ساعات") and not all_hours_var.get():
                            all_hours_var.set(True)
                    elif filter_category == "errors":
                        if not any(selected_errors_vars[k].get() for k in selected_errors_vars if k != "همه خطاها") and not all_errors_var.get():
                            all_errors_var.set(True)
            
            update_selected_filters_display()


        if filter_type == "date_range":
            ctk.CTkLabel(scrollable_checkbox_frame, text=process_persian_text_for_matplotlib("از تاریخ:"),
                         font=("Vazirmatn Regular", 9), text_color="#333333").pack(side=tk.RIGHT, padx=5, pady=5)
            
            start_date_entry = ctk.CTkEntry(scrollable_checkbox_frame, textvariable=selected_date_range_vars["start_date"],
                                            width=100, font=("Vazirmatn Regular", 9))
            start_date_entry.pack(side=tk.RIGHT, padx=5, pady=5)
            start_date_entry.bind("<Return>", lambda event: update_selection("date_range", None, None))
            start_date_entry.bind("<FocusOut>", lambda event: update_selection("date_range", None, None))

            ctk.CTkLabel(scrollable_checkbox_frame, text=process_persian_text_for_matplotlib("تا تاریخ:"),
                         font=("Vazirmatn Regular", 9), text_color="#333333").pack(side=tk.RIGHT, padx=5, pady=5)
            
            end_date_entry = ctk.CTkEntry(scrollable_checkbox_frame, textvariable=selected_date_range_vars["end_date"],
                                          width=100, font=("Vazirmatn Regular", 9))
            end_date_entry.pack(side=tk.RIGHT, padx=5, pady=5)
            end_date_entry.bind("<Return>", lambda event: update_selection("date_range", None, None))
            end_date_entry.bind("<FocusOut>", lambda event: update_selection("date_range", None, None))

            selected_date_range_vars["start_date"].set(current_selected_filters_display["date_range"].get("start_date", (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')))
            selected_date_range_vars["end_date"].set(current_selected_filters_display["date_range"].get("end_date", datetime.now().strftime('%Y-%m-%d')))
            update_selection("date_range", None, None)

        elif filter_type == "weekdays":
            weekday_names = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]
            all_items_list = list(range(7))
            
            all_weekdays_chk = create_checkbox_or_radio(all_option_frame, "همه روزها", all_weekdays_var,
                                     lambda v=all_weekdays_var: update_selection("weekdays", "همه روزها", v), is_all_option=True)
            all_weekdays_chk.pack(anchor='e')

            _set_individual_checkbox_states("weekdays", all_weekdays_var, selected_weekdays_vars, all_items_list)

            for i, name in enumerate(weekday_names):
                create_checkbox_or_radio(scrollable_checkbox_frame, name, selected_weekdays_vars[i],
                                lambda idx=i, var=selected_weekdays_vars[i]: update_selection("weekdays", idx, var),
                                is_radio=False).pack(side=tk.RIGHT, padx=5, pady=5)
            
            update_selected_filters_display()

        elif filter_type == "hours":
            all_items_list = list(range(24))
            
            all_hours_chk = create_checkbox_or_radio(all_option_frame, "همه ساعات", all_hours_var,
                                     lambda v=all_hours_var: update_selection("hours", "همه ساعات", v), is_all_option=True)
            all_hours_chk.pack(anchor='e')

            _set_individual_checkbox_states("hours", all_hours_var, selected_hours_vars, all_items_list)

            for i in range(24):
                create_checkbox_or_radio(scrollable_checkbox_frame, f"{i:02d}:00", selected_hours_vars[i],
                                lambda idx=i, var=selected_hours_vars[i]: update_selection("hours", idx, var),
                                is_radio=False).pack(side=tk.RIGHT, padx=5, pady=5)
            
            update_selected_filters_display()

        elif filter_type == "trade_type":
            trade_types = ["همه", "Profit", "Loss", "RF"]
            
            for t_type_raw in trade_types:
                radio_button = create_checkbox_or_radio(scrollable_checkbox_frame, t_type_raw, selected_trade_type_var,
                                        lambda tt=t_type_raw: update_selection("trade_type", tt, None),
                                        is_radio=True)
                radio_button.pack(side=tk.RIGHT, padx=5, pady=5)
            
            update_selected_filters_display()

        elif filter_type == "errors":
            all_items_list = db_manager.get_all_errors()
            
            all_errors_chk = create_checkbox_or_radio(all_option_frame, "همه خطاها", all_errors_var,
                                     lambda v=all_errors_var: update_selection("errors", "همه خطاها", v), is_all_option=True)
            all_errors_chk.pack(anchor='e')

            _set_individual_checkbox_states("errors", all_errors_var, selected_errors_vars, all_items_list)

            for error_name in all_items_list:
                create_checkbox_or_radio(scrollable_checkbox_frame, error_name, selected_errors_vars[error_name],
                                        lambda err=error_name, var=selected_errors_vars[error_name]: update_selection("errors", err, var),
                                        is_radio=False).pack(side=tk.RIGHT, padx=5, pady=5)
            
            update_selected_filters_display()

    # -------------------------------------------------------------------------
    # توابع نمودار و آمار
    # -------------------------------------------------------------------------
    fig_line, ax_line = plt.subplots(figsize=(6, 4), dpi=100)
    canvas_line = FigureCanvasTkAgg(fig_line, master=chart_panel)
    canvas_widget_line = canvas_line.get_tk_widget()
    canvas_widget_line.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    fig_line.patch.set_facecolor('white')
    ax_line.set_facecolor('white')

    fig_pie, ax_pie = plt.subplots(figsize=(6, 6), dpi=100)
    fig_pie.patch.set_facecolor('white')
    ax_pie.set_facecolor('white')


    def update_line_chart(hourly_data, total_trades_in_range):
        ax_line.clear()

        hours = list(range(24))
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
        ax_line.bar(hours, rf_counts, bar_width, bottom=[profit_counts[i] + loss_counts[i] + rf_counts[i] for i in range(24)], label=process_persian_text_for_matplotlib('ریسک‌فری'), color='#42A5F5')

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
        # دریافت تاریخ از متغیرهای selected_date_range_vars
        start_date_str = selected_date_range_vars["start_date"].get()
        end_date_str = selected_date_range_vars["end_date"].get()

        # اعتبارسنجی تاریخ (می‌تواند گسترده‌تر شود)
        try:
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if start_date_obj > end_date_obj:
                messagebox.showwarning(process_persian_text_for_matplotlib("خطا در تاریخ"), process_persian_text_for_matplotlib("تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد."))
                # برگردوندن تاریخ‌های فعلی به حالت قبلی
                selected_date_range_vars["start_date"].set(current_selected_filters_display["date_range"].get("start_date", (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')))
                selected_date_range_vars["end_date"].set(current_selected_filters_display["date_range"].get("end_date", datetime.now().strftime('%Y-%m-%d')))
                return
        except ValueError:
            messagebox.showwarning(process_persian_text_for_matplotlib("خطا در تاریخ"), process_persian_text_for_matplotlib("فرمت تاریخ نامعتبر است. لطفاً از فرمت YYYY-MM-DD استفاده کنید."))
            # برگردوندن تاریخ‌های فعلی به حالت قبلی
            selected_date_range_vars["start_date"].set(current_selected_filters_display["date_range"].get("start_date", (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')))
            selected_date_range_vars["end_date"].set(current_selected_filters_display["date_range"].get("end_date", datetime.now().strftime('%Y-%m-%d')))
            return

        current_selected_filters_display["date_range"] = {"start_date": start_date_str, "end_date": end_date_str}

        selected_weekdays = [i for i, var in selected_weekdays_vars.items() if var.get()]
        selected_hours = [i for i, var in selected_hours_vars.items() if var.get()]
        selected_trade_type = selected_trade_type_var.get()
        selected_errors_filter = [err for err, var in selected_errors_vars.items() if var.get()]


        # منطق نهایی برای `current_selected_filters_display` بر اساس `all_..._var`
        if all_weekdays_var.get():
            current_selected_filters_display["weekdays"] = list(range(7))
        else:
            current_selected_filters_display["weekdays"] = selected_weekdays

        if all_hours_var.get():
            current_selected_filters_display["hours"] = list(range(24))
        else:
            current_selected_filters_display["hours"] = selected_hours

        all_db_errors = db_manager.get_all_errors()
        if all_errors_var.get():
            current_selected_filters_display["errors"] = all_db_errors
        else:
            current_selected_filters_display["errors"] = selected_errors_filter

        current_selected_filters_display["trade_type"] = selected_trade_type
        
        update_selected_filters_display()

        all_relevant_trades = db_manager.get_trades_for_hourly_analysis(
            current_selected_filters_display["date_range"]["start_date"],
            current_selected_filters_display["date_range"]["end_date"],
            current_selected_filters_display["trade_type"]
        )

        filtered_trades_for_analysis = []
        current_display_timezone = pytz.timezone(db_manager.get_default_timezone())

        for trade in all_relevant_trades:
            try:
                utc_naive_dt = datetime.strptime(f"{trade['date']} {trade['time']}", "%Y-%m-%d %H:%M")
                utc_aware_dt = pytz.utc.localize(utc_naive_dt)
                display_aware_dt = utc_aware_dt.astimezone(current_display_timezone)
                
                weekday_in_display_tz = display_aware_dt.weekday()
                hour_in_display_tz = display_aware_dt.hour

                if current_selected_filters_display["weekdays"] and weekday_in_display_tz not in current_selected_filters_display["weekdays"]:
                    continue
                if current_selected_filters_display["hours"] and hour_in_display_tz not in current_selected_filters_display["hours"]:
                    continue

                # فیلتر کردن بر اساس خطاها
                # اگر فیلتر خطا فعال بود و ترید خطایی نداشت، این ترید باید رد شود
                if current_selected_filters_display["errors"] and not trade['errors']:
                    continue
                # اگر فیلتر خطا فعال بود و ترید خطا داشت، بررسی کن آیا خطاهای ترید در فیلتر موجود هستن
                elif current_selected_filters_display["errors"] and trade['errors']:
                    trade_errors_list = [e.strip() for e in trade['errors'].split(',') if e.strip()]
                    if not any(err_filter in trade_errors_list for err_filter in current_selected_filters_display["errors"]):
                        continue
                
                filtered_trades_for_analysis.append(trade)

            except Exception as e:
                # این ارور "name 'err' is not defined" به دلیل اینکه trade['errors'] خالی باشه و حلقه for in trade_errors_list
                # اجرا نشه، و بعد سعی کنیم از err استفاده کنیم، پیش میاد.
                # با این منطق بالا، این مشکل حل میشه چون قبل از استفاده از trade['errors'] چک میشه.
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

                if trade['errors']:
                    trade_errors_list = [e.strip() for e in trade['errors'].split(',') if e.strip()]
                    # اگر فیلتر خطا غیرفعال بود (یعنی "همه" انتخاب شده)
                    # یا اگر فیلتر خطا فعال بود و این خطا جزو انتخاب شده‌ها بود
                    # اینجا از `any` استفاده می‌کنم تا `err` تعریف شده باشه.
                    if not current_selected_filters_display["errors"] or any(e in current_selected_filters_display["errors"] for e in trade_errors_list):
                        all_filtered_errors_for_pie.extend(trade_errors_list) # از extend استفاده کن برای اضافه کردن همه آیتم‌ها
                        # اگر فقط خطاهای فیلتر شده مد نظر است:
                        # filtered_errors_for_this_trade = [e for e in trade_errors_list if e in current_selected_filters_display["errors"]]
                        # all_filtered_errors_for_pie.extend(filtered_errors_for_this_trade)
                # اگر trade['errors'] خالی بود، و current_selected_filters_display["errors"] هم خالی بود (یعنی "همه خطاها" انتخاب شده)، نباید چیزی اضافه بشه.
                # اگر current_selected_filters_display["errors"] پر بود (فیلتر خاصی اعمال شده)، ولی trade['errors'] خالی بود، نباید چیزی اضافه بشه.

            except Exception as e:
                print(f"Error processing trade {trade.get('id')}: {e}")
                continue

        error_frequency_counts = Counter(all_filtered_errors_for_pie)

        update_line_chart(hourly_profit_loss_rf_counts, total_trades_count)
        # update_pie_chart(error_frequency_counts) # فعلاً غیرفعال

    # اولین بار که پنجره باز می‌شود، فیلترهای پیش‌فرض را نمایش دهد
    current_selected_filters_display["date_range"] = {
        "start_date": (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        "end_date": datetime.now().strftime('%Y-%m-%d')
    }
    current_selected_filters_display["weekdays"] = list(range(7))
    current_selected_filters_display["hours"] = list(range(24))
    current_selected_filters_display["trade_type"] = "همه"
    current_selected_filters_display["errors"] = db_manager.get_all_errors()

    all_weekdays_var = ctk.BooleanVar(value=True)
    all_hours_var = ctk.BooleanVar(value=True)
    all_errors_var = ctk.BooleanVar(value=True)


    show_filter_options("date_range", color_date)
    update_report_data()

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

    root_test = ctk.CTk()
    root_test.withdraw()

    mock_open_windows = []
    show_hourly_analysis_report_window(root_test, mock_open_windows)
    root_test.mainloop()