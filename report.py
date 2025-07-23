# report.py

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk # For Treeview in template selection dialog
from persian_chart_utils import process_persian_text_for_matplotlib, set_titlebar_text
import db_manager
import json
from report_filters import DateRangeFilterFrame 
from datetime import datetime, timedelta 
import pytz 

# Import the new summary frame
from report_files.report_filter_summary_frame import ReportFilterSummaryFrame
# Import the new report details frame
from report_files.report_details import ReportDetailsFrame 

class ReportWindow(ctk.CTkToplevel):
    def __init__(self, parent_root, open_toplevel_windows_list, initial_filters=None):
        super().__init__(parent_root)
        self.parent_root = parent_root
        self.open_toplevel_windows_list = open_toplevel_windows_list

        self.title_text = "گزارش جامع تریدها"
        self.title(process_persian_text_for_matplotlib(self.title_text))
        set_titlebar_text(self, self.title_text)

        self.transient(parent_root)
        self.grab_set()
        self.resizable(True, True)

        self.open_toplevel_windows_list.append(self)

        def on_close():
            if self in self.open_toplevel_windows_list:
                self.open_toplevel_windows_list.remove(self)
            self.destroy()

        self.protocol("WM_DELETE_WINDOW", on_close)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        win_width = int(screen_width * 0.9)
        win_height = int(screen_height * 0.9)

        x = (screen_width / 2) - (win_width / 2)
        y = (screen_height / 2) - (win_height / 2)

        self.geometry(f'{win_width}x{win_height}+{int(x)}+{int(y)}')
        self.configure(fg_color="#F0F2F5")

        self.current_filters = {} 
        self.current_template_name = ""
        self.all_trades_data = [] 

        self.grid_columnconfigure(0, weight=1) 
        # ردیف 0 (برای header_frame) یک سوم و ردیف 1 (برای main_content_frame) دو سوم ارتفاع را می‌گیرد.
        self.grid_rowconfigure(0, weight=2) # برای header_frame (حدود 1/3)
        self.grid_rowconfigure(1, weight=1) # برای main_content_frame (حدود 2/3)

        # Header Frame (top of the window) - Now houses ReportDetailsFrame
        self.header_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=8)
        self.header_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=15) # Changed sticky to nsew
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_rowconfigure(0, weight=1) # ReportDetailsFrame باید تمام فضای موجود در Header Frame را پر کند.

        # این ReportDetailsFrame در واقع محتوای اصلی بخش بالای ReportWindow است
        self.report_details_frame_instance = ReportDetailsFrame(self.header_frame, fg_color="transparent")
        self.report_details_frame_instance.grid(row=0, column=0, sticky="nsew")


        # Main Content Frame (below header)
        self.main_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0,15))
        
        self.main_content_frame.grid_columnconfigure(0, weight=1) 
        self.main_content_frame.grid_columnconfigure(1, weight=0, minsize=400) # ستون سمت راست برای فیلترها (عرض ثابت)
        self.main_content_frame.grid_rowconfigure(0, weight=1) # این ردیف باید تمام فضای عمودی موجود خود را بگیرد.

        # --- Filter Summary Column (Right Side) ---
        self.filter_summary_column = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.filter_summary_column.grid(row=0, column=1, sticky="nsew", padx=(10,0))
        self.filter_summary_column.grid_columnconfigure(0, weight=1)
        self.filter_summary_column.grid_rowconfigure(0, weight=1) # این ردیف باید تمام فضای موجود در filter_summary_column را بگیرد.

        self.report_filter_summary_frame = ReportFilterSummaryFrame(
            self.filter_summary_column, # parent is filter_summary_column
            fg_color="white",
            corner_radius=8,
            on_change_date_range_callback=self._show_date_range_dialog,
            on_change_template_callback=self._show_template_selection_dialog 
        )
        self.report_filter_summary_frame.grid(row=0, column=0, sticky="nsew")


        # --- Report Details Column (Left Side) - Now houses only stat panels and trades list ---
        self.report_details_column = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.report_details_column.grid(row=0, column=0, sticky="nsew")
        # تغییر اینجا: پنل‌های آماری (ردیف 0) فضای کمی بگیرند و لیست تریدها (ردیف 1) بقیه فضا را بگیرد.
        self.report_details_column.grid_columnconfigure(0, weight=1) 
        self.report_details_column.grid_rowconfigure(0, weight=0) # برای stat_panels_frame (کوچک)
        self.report_details_column.grid_rowconfigure(1, weight=1) # برای trades_list_frame (بیشتر فضا)

        # Stat Panels Frame
        self.stat_panels_frame = ctk.CTkFrame(self.report_details_column, fg_color="transparent")
        self.stat_panels_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        # 5 columns for stat panels
        self.stat_panels_frame.grid_columnconfigure((0,1,2,3,4), weight=1) 

        # Placeholder Stat Panels - Set height here
        self.stat_labels = []
        for i in range(5):
            panel = ctk.CTkFrame(self.stat_panels_frame, fg_color="white", corner_radius=8, height=200) 
            panel.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            panel.grid_propagate(False) 
            label = ctk.CTkLabel(panel, text=process_persian_text_for_matplotlib(f"آمار آماری {i+1}\n0"), font=("Vazirmatn", 12))
            label.pack(expand=True)
            self.stat_labels.append(label)


        # Trades List Frame (Actual Treeview for trades) - Set height here
        self.trades_list_frame = ctk.CTkFrame(self.report_details_column, fg_color="white", corner_radius=8, height=300) 
        self.trades_list_frame.grid(row=1, column=0, sticky="nsew")
        self.trades_list_frame.grid_columnconfigure(0, weight=1)
        self.trades_list_frame.grid_rowconfigure(0, weight=1)
        self.trades_list_frame.grid_propagate(False) 


        # Treeview for trades
        trades_style = ttk.Style()
        trades_style.theme_use("clam")
        trades_style.configure("ReportTrades.Treeview",
                               background=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][0] if ctk.get_appearance_mode() == "Light" else "#2B2B2B",
                               foreground=ctk.ThemeManager.theme["CTkLabel"]["text_color"][0] if ctk.get_appearance_mode() == "Light" else "white",
                               fieldbackground=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][0] if ctk.get_appearance_mode() == "Light" else "#2B2B2B",
                               rowheight=25,
                               borderwidth=0,
                               highlightthickness=0,
                               font=("Vazirmatn", 10))
        trades_style.map('ReportTrades.Treeview',
                         background=[('selected', '#3B8ED0')],
                         foreground=[('selected', 'white')])
        trades_style.configure("ReportTrades.Treeview.Heading",
                               font=("Vazirmatn", 10, "bold"),
                               background="#007BFF",
                               foreground="white",
                               padding=[5, 3],
                               relief="flat")
        trades_style.map("ReportTrades.Treeview.Heading",
                         background=[('active', '#0056B3')])

        self.trades_tree = ttk.Treeview(self.trades_list_frame, 
                                        columns=("ID", "Date", "Time", "Symbol", "Entry", "Exit", "Profit", "Errors", "Size", "PositionID", "Type", "ActualProfit"), 
                                        show="headings", style="ReportTrades.Treeview")
        
        # Define columns and headings
        self.trades_tree.heading("ID", text="ID")
        self.trades_tree.heading("Date", text=process_persian_text_for_matplotlib("تاریخ"))
        self.trades_tree.heading("Time", text=process_persian_text_for_matplotlib("ساعت"))
        self.trades_tree.heading("Symbol", text=process_persian_text_for_matplotlib("نماد"))
        self.trades_tree.heading("Entry", text=process_persian_text_for_matplotlib("ورود"))
        self.trades_tree.heading("Exit", text=process_persian_text_for_matplotlib("خروج"))
        self.trades_tree.heading("Profit", text=process_persian_text_for_matplotlib("نتیجه"))
        self.trades_tree.heading("Errors", text=process_persian_text_for_matplotlib("اشتباهات"))
        self.trades_tree.heading("Size", text=process_persian_text_for_matplotlib("سایز"))
        self.trades_tree.heading("PositionID", text="Position ID")
        self.trades_tree.heading("Type", text=process_persian_text_for_matplotlib("نوع"))
        self.trades_tree.heading("ActualProfit", text=process_persian_text_for_matplotlib("مقدار سود/ضرر"))

        # Configure column widths (adjust as needed)
        self.trades_tree.column("ID", width=40, stretch=tk.NO, anchor='center')
        self.trades_tree.column("Date", width=90, stretch=tk.NO, anchor='center')
        self.trades_tree.column("Time", width=60, stretch=tk.NO, anchor='center')
        self.trades_tree.column("Symbol", width=80, stretch=tk.NO, anchor='center')
        self.trades_tree.column("Entry", width=70, stretch=tk.NO, anchor='center')
        self.trades_tree.column("Exit", width=70, stretch=tk.NO, anchor='center')
        self.trades_tree.column("Profit", width=60, stretch=tk.NO, anchor='center')
        self.trades_tree.column("Errors", width=150, stretch=tk.YES, anchor='e') 
        self.trades_tree.column("Size", width=50, stretch=tk.NO, anchor='center')
        self.trades_tree.column("PositionID", width=80, stretch=tk.NO, anchor='center')
        self.trades_tree.column("Type", width=50, stretch=tk.NO, anchor='center')
        self.trades_tree.column("ActualProfit", width=100, stretch=tk.NO, anchor='center')


        self.trades_tree.grid(row=0, column=0, sticky="nsew")

        trades_scrollbar_y = ctk.CTkScrollbar(self.trades_list_frame, command=self.trades_tree.yview)
        trades_scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.trades_tree.configure(yscrollcommand=trades_scrollbar_y.set)

        trades_scrollbar_x = ctk.CTkScrollbar(self.trades_list_frame, orientation="horizontal", command=self.trades_tree.xview)
        trades_scrollbar_x.grid(row=1, column=0, sticky="ew")
        self.trades_tree.configure(xscrollcommand=trades_scrollbar_x.set)

        # Initial load of report data
        if initial_filters:
            self._apply_selected_template(initial_filters)
        else:
            self._set_default_filters()
            self._load_report_data() 

    def _set_default_filters(self):
        """Sets a default set of filters if no initial filters are provided."""
        today = datetime.now().date()
        last_week_start = today - timedelta(days=6) 
        
        self.current_template_name = process_persian_text_for_matplotlib("پیش‌فرض (هفته اخیر)")
        
        self.current_filters = {
            "date_range": {
                "start_date": last_week_start.strftime('%Y-%m-%d'),
                "end_date": today.strftime('%Y-%m-%d'),
                "preset": "last_week"
            },
            "instruments": "همه", 
            "sessions": "همه", 
            "trade_type": "همه", 
            "errors": "همه خطاها", 
            "hourly": {"mode": "hourly_segmentation", "intervals": [], "granularity": 60}, 
            "weekday": "همه" 
        }

    def _apply_selected_template(self, filters_data):
        """Applies filters from a selected template and reloads the report."""
        template_name = filters_data.pop('template_name', process_persian_text_for_matplotlib("نامشخص")) 
        self.current_template_name = template_name
        
        default_filter_structure = {
            "date_range": {"start_date": None, "end_date": None, "preset": "custom"},
            "instruments": "همه", 
            "sessions": "همه", 
            "trade_type": "همه", 
            "errors": "همه خطاها", 
            "hourly": {"mode": "hourly_segmentation", "intervals": [], "granularity": 60},
            "weekday": "همه" 
        }
        
        processed_filters = default_filter_structure.copy()
        for key, value in filters_data.items():
            processed_filters[key] = value

        self.current_filters = processed_filters 
        self._load_report_data()

    def _load_report_data(self):
        """
        Loads trades data and updates UI based on self.current_filters.
        Applies all specified filters.
        """
        self.report_filter_summary_frame.update_summary(self.current_template_name, self.current_filters)
        
        for item in self.trades_tree.get_children():
            self.trades_tree.delete(item)

        user_display_timezone = db_manager.get_default_timezone()
        all_trades = db_manager.get_all_trades(user_display_timezone) 

        filtered_trades = all_trades 

        # 1. Apply Date Range Filter
        date_range_filter = self.current_filters.get("date_range", {})
        start_date_str = date_range_filter.get("start_date")
        end_date_str = date_range_filter.get("end_date")

        if start_date_str and end_date_str:
            try:
                start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                filtered_trades = [
                    trade for trade in filtered_trades 
                    if start_date_obj <= datetime.strptime(trade['date'], '%Y-%m-%d').date() <= end_date_obj
                ]
            except ValueError as e:
                print(f"Error parsing date strings in _load_report_data for date_range: {e}. Skipping date filter.")
        
        # 2. Apply Instrument Filter
        selected_instruments = self.current_filters.get("instruments", "همه")
        if selected_instruments != "همه" and isinstance(selected_instruments, list) and selected_instruments:
            filtered_trades = [trade for trade in filtered_trades if trade['symbol'] in selected_instruments]

        # 3. Apply Trade Type Filter
        selected_trade_type = self.current_filters.get("trade_type", "همه")
        if selected_trade_type != "همه":
            filtered_trades = [trade for trade in filtered_trades if trade['profit'] == selected_trade_type]

        # 4. Apply Errors Filter
        selected_errors = self.current_filters.get("errors", "همه خطاها")
        if selected_errors != "همه خطاها": 
            if isinstance(selected_errors, list) and selected_errors: 
                filtered_trades = [
                    trade for trade in filtered_trades 
                    if trade['errors'] and any(err.strip() in selected_errors for err in trade['errors'].split(','))
                ]
            elif isinstance(selected_errors, list) and not selected_errors: 
                filtered_trades = [
                    trade for trade in filtered_trades 
                    if not trade['errors'] or trade['errors'].strip() == ""
                ]


        # 5. Apply Weekday Filter
        selected_weekdays = self.current_filters.get("weekday", "همه")
        if selected_weekdays != "همه" and isinstance(selected_weekdays, list) and selected_weekdays:
            filtered_trades = [
                trade for trade in filtered_trades 
                if datetime.strptime(trade['date'], '%Y-%m-%d').weekday() in selected_weekdays
            ]

        # 6. Apply Session & Hourly Filter
        selected_sessions = self.current_filters.get("sessions", "همه")
        hourly_filter_data = self.current_filters.get("hourly", {})
        hourly_mode = hourly_filter_data.get("mode")

        trades_after_session_and_hourly_filter = []

        if selected_sessions == "همه" and hourly_mode == "full_session":
            trades_after_session_and_hourly_filter = filtered_trades
        else:
            all_session_times_display = db_manager.get_session_times_with_display_utc(user_display_timezone)

            for trade in filtered_trades:
                trade_dt_obj = datetime.strptime(f"{trade['date']} {trade['time']}", '%Y-%m-%d %H:%M')
                
                is_in_selected_session = False
                if selected_sessions == "همه":
                    is_in_selected_session = True 
                elif isinstance(selected_sessions, list) and selected_sessions:
                    for sess_key in selected_sessions:
                        session_detail = all_session_times_display.get(sess_key)
                        if session_detail and db_manager._is_trade_in_time_interval(trade_dt_obj, session_detail['start_display'], session_detail['end_display']):
                            is_in_selected_session = True
                            break
                elif isinstance(selected_sessions, list) and not selected_sessions: 
                    is_in_selected_session = False
                
                if not is_in_selected_session:
                    continue 

                is_in_hourly_interval = False
                if hourly_mode == "full_session":
                    is_in_hourly_interval = True 
                elif hourly_mode == "session_segmentation":
                    segments_to_check = hourly_filter_data.get("segments", [])
                    if not segments_to_check: 
                        is_in_hourly_interval = False
                    else:
                        for segment in segments_to_check:
                            if db_manager._is_trade_in_time_interval(trade_dt_obj, segment['start'], segment['end']):
                                is_in_hourly_interval = True
                                break
                elif hourly_mode in ["hourly_segmentation", "half_hourly_segmentation", "quarter_hourly_segmentation"]:
                    intervals_to_check = hourly_filter_data.get("intervals", [])
                    if not intervals_to_check: 
                        is_in_hourly_interval = False
                    else:
                        for interval in intervals_to_check:
                            if db_manager._is_trade_in_time_interval(trade_dt_obj, interval['start'], interval['end']):
                                is_in_hourly_interval = True
                                break
                else: 
                    is_in_hourly_interval = False 
                
                if is_in_hourly_interval:
                    trades_after_session_and_hourly_filter.append(trade)
            
            filtered_trades = trades_after_session_and_hourly_filter


        for trade in filtered_trades:
            self.trades_tree.insert("", "end", values=(
                trade['id'],
                trade['date'],
                trade['time'],
                trade['symbol'],
                trade['entry'],
                trade['exit'],
                trade['profit'],
                trade['errors'],
                trade['size'],
                trade['position_id'],
                trade['type'],
                trade['actual_profit_amount']
            ))
        
        num_trades = len(filtered_trades)
        self.stat_labels[0].configure(text=process_persian_text_for_matplotlib(f"تعداد تریدها:\n{num_trades}"))
        
        total_profit_amount = sum(t['actual_profit_amount'] for t in filtered_trades if t['actual_profit_amount'] is not None)
        self.stat_labels[1].configure(text=process_persian_text_for_matplotlib(f"سود کل:\n{total_profit_amount:.2f}"))

        profit_trades_count = sum(1 for t in filtered_trades if t['profit'] == 'Profit')
        loss_trades_count = sum(1 for t in filtered_trades if t['profit'] == 'Loss')
        rf_trades_count = sum(1 for t in filtered_trades if t['profit'] == 'RF')
        
        total_decisive_trades = profit_trades_count + loss_trades_count
        win_rate = (profit_trades_count / total_decisive_trades * 100) if total_decisive_trades > 0 else 0
        
        self.stat_labels[2].configure(text=process_persian_text_for_matplotlib(f"وین ریت:\n{win_rate:.2f}%"))
        self.stat_labels[3].configure(text=process_persian_text_for_matplotlib(f"ترید سودده:\n{profit_trades_count}"))
        self.stat_labels[4].configure(text=process_persian_text_for_matplotlib(f"ترید ضررده:\n{loss_trades_count}"))

        # Update the content of ReportDetailsFrame
        self.report_details_frame_instance.update_report_content(filtered_trades, self.current_filters, self.current_template_name)


    def _show_template_selection_dialog(self):
        """
        Displays a dialog for selecting a saved report template.
        """
        dialog = ctk.CTkToplevel(self)
        dialog.title(process_persian_text_for_matplotlib("انتخاب فیلتر گزارش"))
        set_titlebar_text(dialog, process_persian_text_for_matplotlib("انتخاب فیلتر گزارش"))
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        dialog_width = 450
        dialog_height = 400
        x = self.winfo_x() + (self.winfo_width() / 2) - (dialog_width / 2)
        y = self.winfo_y() + (self.winfo_height() / 2) - (dialog_height / 2)
        dialog.geometry(f"{dialog_width}x{dialog_height}+{int(x)}+{int(y)}")

        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=0)

        # Treeview for templates
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TemplateDialog.Treeview",
                        background=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][0] if ctk.get_appearance_mode() == "Light" else "#2B2B2B",
                        foreground=ctk.ThemeManager.theme["CTkLabel"]["text_color"][0] if ctk.get_appearance_mode() == "Light" else "white",
                        fieldbackground=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][0] if ctk.get_appearance_mode() == "Light" else "#2B2B2B",
                        rowheight=30,
                        borderwidth=0,
                        highlightthickness=0,
                        font=("Vazirmatn", 11))
        style.map('TemplateDialog.Treeview',
                  background=[('selected', '#3B8ED0')],
                  foreground=[('selected', 'white')])
        style.configure("TemplateDialog.Treeview.Heading",
                        font=("Vazirmatn", 11, "bold"),
                        background="#007BFF",
                        foreground="white",
                        padding=[10, 5],
                        relief="flat")
        style.map("TemplateDialog.Treeview.Heading",
                  background=[('active', '#0056B3')])

        templates_tree = ttk.Treeview(main_frame, columns=("ID", "Name"), show="headings", style="TemplateDialog.Treeview")
        templates_tree.heading("ID", text="ID")
        templates_tree.heading("Name", text=process_persian_text_for_matplotlib("نام فیلتر"))
        templates_tree.column("ID", width=50, stretch=tk.NO, anchor='center')
        templates_tree.column("Name", stretch=tk.YES, anchor='e')
        templates_tree.grid(row=0, column=0, sticky="nsew")

        templates_scrollbar = ctk.CTkScrollbar(main_frame, command=templates_tree.yview)
        templates_scrollbar.grid(row=0, column=1, sticky="ns")
        templates_tree.configure(yscrollcommand=templates_scrollbar.set)

        # Populate templates
        templates = db_manager.get_report_templates()
        for template in templates:
            templates_tree.insert("", "end", iid=str(template['id']),
                                   values=(template['id'], process_persian_text_for_matplotlib(template['name'])))

        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        button_frame.grid_columnconfigure((0,1), weight=1)

        def on_select_template():
            selected_item = templates_tree.selection()
            if not selected_item:
                messagebox.showwarning(process_persian_text_for_matplotlib("هشدار"), 
                                       process_persian_text_for_matplotlib("لطفاً یک فیلتر را انتخاب کنید."), parent=dialog)
                return
            template_id = int(templates_tree.item(selected_item[0], 'values')[0])
            template_data = db_manager.get_report_template_by_id(template_id)
            if template_data and 'filters_json' in template_data:
                filters_to_apply = template_data['filters_json']
                filters_to_apply['template_name'] = template_data['name'] 
                self._apply_selected_template(filters_to_apply)
                dialog.destroy()
            else:
                messagebox.showerror(process_persian_text_for_matplotlib("خطا"), 
                                     process_persian_text_for_matplotlib("خطا در بارگذاری فیلتر."), parent=dialog)

        def on_cancel():
            dialog.destroy()

        select_button = ctk.CTkButton(button_frame, text=process_persian_text_for_matplotlib("انتخاب"), command=on_select_template, font=("Vazirmatn", 12), fg_color="#28A745", hover_color="#218838")
        select_button.grid(row=0, column=0, padx=5, sticky="ew")

        cancel_button = ctk.CTkButton(button_frame, text=process_persian_text_for_matplotlib("لغو"), command=on_cancel, font=("Vazirmatn", 12), fg_color="#DC3545", hover_color="#C82333")
        cancel_button.grid(row=0, column=1, padx=5, sticky="ew")

        dialog.wait_window(dialog)


    def _show_date_range_dialog(self, current_date_range_data):
        """
        Displays a dialog for selecting a custom date range.
        Args:
            current_date_range_data (dict): The currently active date range filters.
        """
        dialog = ctk.CTkToplevel(self)
        dialog.title(process_persian_text_for_matplotlib("تغییر بازه تاریخی"))
        set_titlebar_text(dialog, process_persian_text_for_matplotlib("تغییر بازه تاریخی"))
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        dialog_width = 400
        dialog_height = 300 
        x = self.winfo_x() + (self.winfo_width() / 2) - (dialog_width / 2)
        y = self.winfo_y() + (self.winfo_height() / 2) - (dialog_height / 2)
        dialog.geometry(f"{dialog_width}x{dialog_height}+{int(x)}+{int(y)}")

        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=0)

        # Instance of DateRangeFilterFrame
        date_range_filter_frame = DateRangeFilterFrame(main_frame, fg_color="transparent", on_change_callback=None) 
        date_range_filter_frame.grid(row=0, column=0, sticky="nsew")

        # Set initial values based on current_date_range_data
        if current_date_range_data and current_date_range_data.get("start_date") and current_date_range_data.get("end_date"):
            date_range_filter_frame.set_selection(
                current_date_range_data.get("start_date"),
                current_date_range_data.get("end_date"),
                current_date_range_data.get("preset")
            )
        else:
            date_range_filter_frame.initialize_dates() 

        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=1, column=0, pady=10, sticky="ew")
        button_frame.grid_columnconfigure((0,1), weight=1)

        def on_apply_date_range():
            new_date_range_selection = date_range_filter_frame.get_selection()
            self.current_filters['date_range'] = new_date_range_selection
            self._load_report_data() 
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        apply_button = ctk.CTkButton(button_frame, text=process_persian_text_for_matplotlib("اعمال"), command=on_apply_date_range, font=("Vazirmatn", 12), fg_color="#28A745", hover_color="#218838")
        apply_button.grid(row=0, column=0, padx=5, sticky="ew")

        cancel_button = ctk.CTkButton(button_frame, text=process_persian_text_for_matplotlib("لغو"), command=on_cancel, font=("Vazirmatn", 12), fg_color="#DC3545", hover_color="#C82333")
        cancel_button.grid(row=0, column=1, padx=5, sticky="ew")

        dialog.wait_window(dialog)