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
import numpy as np # <<< اضافه شده: برای استفاده از np.linspace در colormap

import arabic_reshaper
from bidi import algorithm as bidi

# تابع پردازش متن فارسی از فایل پیکربندی ایمپورت شده است
from matplotlib_persian_config import process_persian_text_for_matplotlib 

OPEN_TOPLEVEL_WINDOWS = [] 

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
                # print(f"Matplotlib: فونت '{FONT_NAME}' از لیست یافت شد: {font_paths[0]}") # کامنت شده
                break
        else:
            FONT_NAME = font_candidate
            # print(f"Matplotlib: فونت '{FONT_NAME}' یافت شد: {font_paths}") # کامنت شده
            break

if FONT_NAME:
    plt.rcParams['font.family'] = FONT_NAME
    plt.rcParams['font.sans-serif'] = FONT_NAME
    plt.rcParams['axes.unicode_minus'] = False 
    # print(f"Matplotlib: فونت '{FONT_NAME}' برای نمایش فارسی تنظیم شد.") # کامنت شده
else:
    # print("Matplotlib: فونت فارسی مناسب یافت نشد. استفاده از فونت پیش‌فرض Matplotlib.") # کامنت شده
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial'] 
    plt.rcParams['axes.unicode_minus'] = False 
# --- پایان تنظیمات فونت فارسی برای Matplotlib ---

# اگر تابع process_persian_text_for_matplotlib از فایل config ایمپورت شده باشد،
# نیازی به تعریف مجدد آن در اینجا نیست. اما برای حالت مستقل، می‌توان آن را نگه داشت.
# در کد نهایی، اگر از matplotlib_persian_config ایمپورت شود، این تعریف باید حذف گردد.
# در حال حاضر، چون در app.py ایمپورت شده، اینجا نیازی به تعریف مجدد نیست.


def show_hourly_analysis_report_window(parent_root, open_toplevel_windows_list_UNUSED):
    """
    پنجره گزارش آنالیز ساعتی را نمایش می‌دهد.
    فعلاً منطق مینیمایز/ماکسیمایز کردن پنجره‌های دیگر غیرفعال است.
    """
    
    report_win = tk.Toplevel(parent_root)
    report_win.title("گزارش آنالیز ساعتی تریدها") 
    report_win.transient(parent_root)
    report_win.grab_set()
    report_win.resizable(True, True) 

    report_win.protocol("WM_DELETE_WINDOW", report_win.destroy) 

    screen_width = report_win.winfo_screenwidth()
    screen_height = report_win.winfo_screenheight()

    win_width = int(screen_width * 0.8) 
    win_height = int(screen_height * 0.8) 

    x = (screen_width / 2) - (win_width / 2)
    y = (screen_height / 2) - (win_height / 2)

    report_win.geometry(f'{win_width}x{win_height}+{int(x)}+{int(y)}')

    report_win.configure(bg="#F0F2F5") 

    # --- استفاده از PanedWindow برای تغییر اندازه ستون‌ها ---
    main_paned_window = ttk.PanedWindow(report_win, orient=tk.HORIZONTAL)
    main_paned_window.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

    # پنل فیلترها (سمت راست)
    filter_panel = tk.Frame(main_paned_window, bg="white", padx=15, pady=15, relief="flat", bd=0)
    filter_panel.grid_rowconfigure(99, weight=1) 
    main_paned_window.add(filter_panel, weight=1) # وزن اولیه برای PanedWindow

    # پنل محتوای اصلی (سمت چپ)
    content_panel = tk.Frame(main_paned_window, bg="#F0F2F5")
    main_paned_window.add(content_panel, weight=4) # وزن بیشتر برای محتوا


    def set_initial_pane_width():
        if not report_win.winfo_ismapped(): 
            report_win.after(100, set_initial_pane_width)
            return
        
        main_paned_window.update_idletasks() 
        total_width = main_paned_window.winfo_width()
        filter_pane_width = int(total_width * 0.20) 
        main_paned_window.sashpos(0, filter_pane_width) 
        # وزن‌ها را اینجا پس از تنظیم موقعیت sاش تنظیم می‌کنیم تا رفتار resize بهتر باشد.
        main_paned_window.pane(filter_panel, weight=0) # فیلتر پانل ثابت
        main_paned_window.pane(content_panel, weight=1) # محتوا قابل گسترش

    report_win.after(100, set_initial_pane_width) 

    tk.Label(filter_panel, text=process_persian_text_for_matplotlib("تنظیم فیلترها"), font=("Segoe UI", 13, "bold"), bg="white", fg="#202124", justify='right').pack(pady=(0, 15), anchor='e')


    summary_labels = {} 
    
    def create_summary_card(parent, row, col, title, initial_value):
        card_frame = tk.Frame(parent, bg="white", padx=10, pady=10, relief="flat", bd=0)
        card_frame.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        
        tk.Label(card_frame, text=process_persian_text_for_matplotlib(title), font=("Segoe UI", 9), bg="white", fg="#5F6368", justify='right').pack(anchor='e') 
        value_label = tk.Label(card_frame, text=initial_value, font=("Segoe UI", 18, "bold"), bg="white", fg="#202124", justify='right')
        value_label.pack(anchor='e')
        
        return value_label 


    def update_summary_cards(total, profit, loss, rf):
        nonlocal summary_labels 
        summary_labels['total_trades'].config(text=str(total))
        summary_labels['profit_trades'].config(text=str(profit))
        summary_labels['loss_trades'].config(text=str(loss))
        summary_labels['rf_trades'].config(text=str(rf))

    # --- توابع بروزرسانی نمودارها ---
    fig_line, ax_line = plt.subplots(figsize=(6, 4), dpi=100) 
    fig_pie, ax_pie = plt.subplots(figsize=(6, 6), dpi=100) # <<< تغییر اندازه برای نمودار دایره‌ای


    def update_line_chart(hourly_data, total_trades_in_range):
        ax_line.clear()
        
        hours = list(range(24))
        profit_counts = [hourly_data.get(h, {}).get('Profit', 0) for h in hours]
        loss_counts = [hourly_data.get(h, {}).get('Loss', 0) for h in hours]
        rf_counts = [hourly_data.get(h, {}).get('RF', 0) for h in hours]
        
        if total_trades_in_range == 0:
            ax_line.text(0.5, 0.5, process_persian_text_for_matplotlib("داده‌ای برای نمایش نمودار وجود ندارد."), horizontalalignment='center', verticalalignment='center', transform=ax_line.transAxes, fontsize=10, color='gray', fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0])) 
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
            ax_pie.text(0.5, 0.5, process_persian_text_for_matplotlib("داده‌ای برای نمایش نمودار دایره‌ای وجود ندارد."), horizontalalignment='center', verticalalignment='center', transform=ax_pie.transAxes, fontsize=10, color='gray', fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0])) 
            ax_pie.set_xticks([])
            ax_pie.set_yticks([])
            canvas_pie.draw()
            return

        processed_labels_for_pie = [process_persian_text_for_matplotlib(label) for label in labels_raw]
        processed_labels_for_legend = [process_persian_text_for_matplotlib(f"{l_raw} ({s})") for l_raw, s in zip(labels_raw, sizes)]

        # <<< استفاده از colormap با تعداد رنگ‌های کافی و مناسب
        num_colors = len(processed_labels_for_pie)
        # انتخاب colormap بر اساس تعداد اسلایس‌ها
        if num_colors <= 10:
            colors = plt.cm.get_cmap('tab10')(range(num_colors))
        elif num_colors <= 20:
            colors = plt.cm.get_cmap('tab20')(range(num_colors))
        else: # برای تعداد بیشتر، از یک colormap پیوسته استفاده می‌کنیم
            colors = plt.cm.get_cmap('viridis')(np.linspace(0, 1, num_colors))
        # >>>
        
        wedges, texts, autotexts = ax_pie.pie(sizes, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 8, 'fontproperties': fm.FontProperties(family=plt.rcParams['font.family'][0])}, colors=colors, pctdistance=0.85, labels=processed_labels_for_pie) 
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

    # --- تابع اصلی برای به‌روزرسانی گزارش بر اساس فیلترها ---
    def update_report_data():
        start_date_str = from_date_var.get()
        end_date_str = to_date_var.get()
        selected_trade_type_processed = trade_type_var.get() # مقدار پردازش شده از combobox
        
        # <<< تبدیل مقدار پردازش شده "همه" به مقدار واقعی "همه" برای دیتابیس
        if selected_trade_type_processed == process_persian_text_for_matplotlib("همه"):
            selected_trade_type = "همه"
        else:
            # اگر 'Profit', 'Loss', 'RF' انتخاب شده باشد
            # این مقادیر در DB انگلیسی ذخیره شده‌اند، پس باید برگردانیم
            if selected_trade_type_processed == process_persian_text_for_matplotlib("Profit"):
                selected_trade_type = "Profit"
            elif selected_trade_type_processed == process_persian_text_for_matplotlib("Loss"):
                selected_trade_type = "Loss"
            elif selected_trade_type_processed == process_persian_text_for_matplotlib("RF"):
                selected_trade_type = "RF"
            else:
                selected_trade_type = "همه" # حالت پیش‌فرض یا خطا
        # >>>
        
        if all_errors_selected_var.get():
            selected_errors_filter = [] 
        else:
            # <<< این قسمت برای دریافت لیبل‌های اصلی (قبل از پردازش)
            selected_errors_filter = [
                err_name_original for err_name_original, var in error_filter_vars.items() 
                if var.get()
            ]
            # >>>

        try:
            # <<< اعتبارسنجی و تبدیل تاریخ
            start_date_dt = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date_dt = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            # >>>

            if start_date_dt > end_date_dt:
                messagebox.showwarning(process_persian_text_for_matplotlib("خطا در تاریخ"), process_persian_text_for_matplotlib("تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد.")) 
                return 
        except ValueError:
            messagebox.showwarning(process_persian_text_for_matplotlib("خطا در تاریخ"), process_persian_text_for_matplotlib("فرمت تاریخ نامعتبر است. لطفاً از فرمت YYYY-MM-DD استفاده کنید.")) 
            return

        # <<< ارسال نام ترید انگلیسی به db_manager
        all_relevant_trades = db_manager.get_trades_for_hourly_analysis(
            start_date_str, end_date_str, selected_trade_type
        )
        # >>>
        
        filtered_trades_for_analysis = []
        for trade in all_relevant_trades:
            if not selected_errors_filter: 
                filtered_trades_for_analysis.append(trade)
            elif trade['errors']:
                trade_errors_list = [e.strip() for e in trade['errors'].split(',') if e.strip()]
                if any(err_filter in trade_errors_list for err_filter in selected_errors_filter):
                    filtered_trades_for_analysis.append(trade)

        hourly_profit_loss_rf_counts = defaultdict(lambda: Counter())
        all_filtered_errors_for_pie = [] 
        
        total_trades_count = len(filtered_trades_for_analysis)
        profit_count = 0
        loss_count = 0
        rf_count = 0

        current_display_timezone = pytz.timezone(db_manager.get_default_timezone())

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
                    for err in trade_errors_list:
                        if not selected_errors_filter or err in selected_errors_filter:
                            all_filtered_errors_for_pie.append(err)

            except Exception as e:
                print(f"Error processing trade {trade.get('id')}: {e}")
                continue
        
        error_frequency_counts = Counter(all_filtered_errors_for_pie)

        update_line_chart(hourly_profit_loss_rf_counts, total_trades_count)
        update_pie_chart(error_frequency_counts)
        update_summary_cards(total_trades_count, profit_count, loss_count, rf_count)

    # فیلتر تاریخ 
    tk.Label(filter_panel, text=process_persian_text_for_matplotlib("بازه تاریخی:"), font=("Segoe UI", 10, "bold"), bg="white", fg="#5F6368", justify='right').pack(pady=(10, 5), anchor='e') 
    date_range_frame = tk.Frame(filter_panel, bg="white")
    date_range_frame.pack(fill='x', padx=5)

    tk.Label(date_range_frame, text=process_persian_text_for_matplotlib("از:"), bg="white", justify='right').pack(side=tk.RIGHT, padx=(0, 5)) 
    from_date_var = tk.StringVar(value=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    from_date_entry = ttk.Entry(date_range_frame, textvariable=from_date_var, width=12) 
    from_date_entry.pack(side=tk.RIGHT, expand=True)
    # <<< اتصال مستقیم به trace_add
    from_date_var.trace_add("write", lambda *args: update_report_data()) 
    # >>>

    tk.Label(date_range_frame, text=process_persian_text_for_matplotlib("تا:"), bg="white", justify='right').pack(side=tk.RIGHT, padx=(10, 5)) 
    to_date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
    to_date_entry = ttk.Entry(date_range_frame, textvariable=to_date_var, width=12) 
    to_date_entry.pack(side=tk.RIGHT, expand=True)
    # <<< اتصال مستقیم به trace_add
    to_date_var.trace_add("write", lambda *args: update_report_data())   
    # >>>


    # فیلتر نوع ترید
    tk.Label(filter_panel, text=process_persian_text_for_matplotlib("نوع ترید:"), font=("Segoe UI", 10, "bold"), bg="white", fg="#5F6368", justify='right').pack(pady=(10, 5), anchor='e') 
    trade_type_var = tk.StringVar(value=process_persian_text_for_matplotlib("همه")) # مقدار پیش‌فرض را پردازش می‌کنیم
    trade_type_options = [process_persian_text_for_matplotlib(opt) for opt in ["همه", "Profit", "Loss", "RF"]] 
    trade_type_combobox = ttk.Combobox(filter_panel, textvariable=trade_type_var, values=trade_type_options, state="readonly", width=25)
    trade_type_combobox.pack(fill='x', padx=5)
    trade_type_combobox.set(process_persian_text_for_matplotlib("همه")) 
    trade_type_combobox.bind("<<ComboboxSelected>>", lambda event: update_report_data()) # <<< تغییر: event را هم بپذیرد


    # فیلتر نوع خطا
    tk.Label(filter_panel, text=process_persian_text_for_matplotlib("فیلتر خطاها:"), font=("Segoe UI", 10, "bold"), bg="white", fg="#5F6368", justify='right').pack(pady=(10, 5), anchor='e') 
    
    error_selection_frame = tk.Frame(filter_panel, bg="white")
    error_selection_frame.pack(fill='both', expand=True, padx=5)

    error_canvas = tk.Canvas(error_selection_frame, bg="white", highlightthickness=0)
    error_scrollbar = ttk.Scrollbar(error_selection_frame, orient="vertical", command=error_canvas.yview)
    scrollable_error_frame = tk.Frame(error_canvas, bg="white")

    scrollable_error_frame.bind(
        "<Configure>",
        lambda e: error_canvas.configure(scrollregion=error_canvas.bbox("all"))
    )

    error_canvas.create_window((0, 0), window=scrollable_error_frame, anchor="nw")
    error_canvas.configure(yscrollcommand=error_scrollbar.set)

    error_canvas.pack(side="left", fill="both", expand=True)
    error_scrollbar.pack(side="right", fill="y")

    all_errors = db_manager.get_all_errors()
    error_filter_vars = {}
    all_errors_selected_var = tk.BooleanVar(value=True) 

    def toggle_all_errors_and_update(): 
        state = all_errors_selected_var.get()
        for var in error_filter_vars.values():
            var.set(state)
        update_report_data() 

    tk.Checkbutton(scrollable_error_frame, text=process_persian_text_for_matplotlib("همه خطاها"), variable=all_errors_selected_var, 
                                     command=toggle_all_errors_and_update, bg="white", anchor='e', justify='right', font=("Segoe UI", 9, "bold")).pack(pady=(0, 5), fill='x') 

    for error_name in all_errors:
        var = tk.BooleanVar(value=True) 
        # <<< تغییر: command را به تابع update_report_data متصل می‌کنیم
        chk = tk.Checkbutton(scrollable_error_frame, text=process_persian_text_for_matplotlib(error_name), variable=var, bg="white", anchor='e', justify='right', command=update_report_data) 
        chk.pack(pady=1, fill='x')
        error_filter_vars[error_name] = var

    apply_filters_button = tk.Button(filter_panel, text=process_persian_text_for_matplotlib("اعمال فیلترها"), command=update_report_data, 
                                      bg="#4285F4", fg="white", font=("Segoe UI", 10, "bold"),
                                      borderwidth=0, relief="flat", padx=10, pady=5,
                                      activebackground="#3367D6", activeforeground="white", cursor="hand2")
    apply_filters_button.pack(side=tk.BOTTOM, fill='x', pady=15, padx=5) 

    content_panel.grid_rowconfigure(0, weight=0) 
    content_panel.grid_rowconfigure(1, weight=3) 
    content_panel.grid_rowconfigure(2, weight=1) 
    content_panel.grid_columnconfigure(0, weight=1) 

    current_tz_label = tk.Label(content_panel, text=process_persian_text_for_matplotlib(""), fg="#5F6368", bg="#F0F2F5", font=("Segoe UI", 9, "italic"), justify='right')
    current_tz_label.grid(row=0, column=0, pady=(0, 10), sticky='ne', padx=10) 

    def update_timezone_display():
        current_tz_name = db_manager.get_default_timezone()
        current_tz_label.config(text=process_persian_text_for_matplotlib(f"⏰ منطقه زمانی فعال شما: {current_tz_name}")) 
    update_timezone_display()

    charts_frame = tk.Frame(content_panel, bg="white", relief="flat", bd=0)
    charts_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 15), padx=10)
    
    charts_frame.grid_columnconfigure(0, weight=1)
    charts_frame.grid_columnconfigure(1, weight=1)
    charts_frame.grid_rowconfigure(0, weight=1)

    line_chart_frame = tk.Frame(charts_frame, bg="white", padx=10, pady=10)
    line_chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 7))

    tk.Label(line_chart_frame, text=process_persian_text_for_matplotlib("روند تریدها در ساعات روز (تعداد)"), font=("Segoe UI", 11, "bold"), bg="white", fg="#202124", justify='right').pack(pady=(0, 10), anchor='e') 
    
    canvas_line = FigureCanvasTkAgg(fig_line, master=line_chart_frame) 
    canvas_widget_line = canvas_line.get_tk_widget()
    canvas_widget_line.pack(fill=tk.BOTH, expand=True)

    pie_chart_frame = tk.Frame(charts_frame, bg="white", padx=10, pady=10)
    pie_chart_frame.grid(row=0, column=1, sticky="nsew", padx=(7, 0))

    tk.Label(pie_chart_frame, text=process_persian_text_for_matplotlib("توزیع خطاهای منتخب (درصد)"), font=("Segoe UI", 11, "bold"), bg="white", fg="#202124", justify='right').pack(pady=(0, 10), anchor='e') 

    canvas_pie = FigureCanvasTkAgg(fig_pie, master=pie_chart_frame) 
    canvas_widget_pie = canvas_pie.get_tk_widget()
    canvas_widget_pie.pack(fill=tk.BOTH, expand=True)

    summary_cards_frame = tk.Frame(content_panel, bg="#F0F2F5")
    summary_cards_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 15)) 
    
    for i in range(4):
        summary_cards_frame.grid_columnconfigure(i, weight=1)

    summary_labels['total_trades'] = create_summary_card(summary_cards_frame, 0, 0, "کل تریدها", "0")
    summary_labels['profit_trades'] = create_summary_card(summary_cards_frame, 0, 1, "تریدهای سودده", "0")
    summary_labels['loss_trades'] = create_summary_card(summary_cards_frame, 0, 2, "تریدهای زیان‌ده", "0")
    summary_labels['rf_trades'] = create_summary_card(summary_cards_frame, 0, 3, "تریدهای ریسک‌فری", "0")


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