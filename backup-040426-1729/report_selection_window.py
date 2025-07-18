# report_selection_window.py

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import os
import sys
from datetime import datetime, timedelta

# Import all modular filter frames
from report_filters import (
    DateRangeFilterFrame,
    InstrumentFilterFrame,
    SessionFilterFrame,
    TradeTypeFilterFrame, # Added
    ErrorFilterFrame, # Added
    HourlyFilterFrame,
    WeekdayFilterFrame
)
from report_detail_frame import ReportDetailFrame

# Import Persian text utility
from persian_chart_utils import process_persian_text_for_matplotlib, set_titlebar_text

class ReportSelectionWindow(ctk.CTkToplevel):
    def __init__(self, parent_root, open_toplevel_windows_list):
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
            
            for filter_key in self.filter_frames:
                # اطمینان حاصل کن که on_change_callback وجود دارد قبل از ست کردن به None
                if hasattr(self.filter_frames[filter_key], 'on_change_callback'):
                    self.filter_frames[filter_key].on_change_callback = None
            
            self.destroy()

        self.protocol("WM_DELETE_WINDOW", on_close)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        win_width = int(screen_width * 0.9)
        win_height = int(screen_height * 0.8)

        x = (screen_width / 2) - (win_width / 2)
        y = (screen_height / 2) - (win_height / 2)

        self.geometry(f'{win_width}x{win_height}+{int(x)}+{int(y)}')
        self.configure(fg_color="#F0F2F5")

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        header_total_width = win_width - (2 * 15)
        self.fixed_buttons_column_width = 150
        self.fixed_filter_content_column_width = int(header_total_width * 0.5)
        self.fixed_summary_column_width = header_total_width - self.fixed_buttons_column_width - self.fixed_filter_content_column_width - (2*10)
        
        if self.fixed_summary_column_width < 100: self.fixed_summary_column_width = 100
        if self.fixed_filter_content_column_width < 200: self.fixed_filter_content_column_width = 200

        self.main_frame.grid_columnconfigure(0, weight=0, minsize=self.fixed_filter_content_column_width + self.fixed_buttons_column_width + 20)
        self.main_frame.grid_columnconfigure(1, weight=0, minsize=self.fixed_summary_column_width)
        self.main_frame.grid_rowconfigure(0, weight=0)
        self.main_frame.grid_rowconfigure(1, weight=1)

        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=8)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        self.header_frame.grid_columnconfigure(0, weight=0, minsize=self.fixed_summary_column_width + (2*10))
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        self.summary_section_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.summary_section_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.summary_section_frame.grid_columnconfigure(0, weight=1)
        self.summary_section_frame.grid_columnconfigure(1, weight=1)
        
        self.summary_title_label = ctk.CTkLabel(self.summary_section_frame, text=process_persian_text_for_matplotlib("خلاصه فیلترها:"),
                                                 font=("Vazirmatn", 14, "bold"), text_color="#202124", anchor='e')
        self.summary_title_label.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))

        self.summary_table_frame = ctk.CTkFrame(self.summary_section_frame, fg_color="transparent")
        self.summary_table_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.summary_table_frame.grid_columnconfigure(0, weight=1)
        self.summary_table_frame.grid_columnconfigure(1, weight=1)


        self.filters_main_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.filters_main_container.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        self.filters_main_container.grid_columnconfigure(0, weight=0, minsize=self.fixed_filter_content_column_width)
        self.filters_main_container.grid_columnconfigure(1, weight=0, minsize=self.fixed_buttons_column_width)
        
        self.filter_content_area = ctk.CTkFrame(self.filters_main_container, fg_color="transparent")
        self.filter_content_area.grid(row=0, column=0, sticky="nsew")
        self.filter_content_area.grid_rowconfigure(0, weight=1)
        self.filter_content_area.grid_columnconfigure(0, weight=1)

        self.filter_buttons_frame = ctk.CTkFrame(self.filters_main_container, fg_color="transparent")
        self.filter_buttons_frame.grid(row=0, column=1, padx=(10, 0), sticky="ns")
        
        self.filter_frames = {}
        self.filter_buttons = {}
        self.active_filter_frame = None

        # --- Filter Modules Instances ---
        # All filter frames are instantiated with a ref to self._on_filter_changed as callback.
        self.filter_frames["date_range"] = DateRangeFilterFrame(self.filter_content_area, on_change_callback=self._on_filter_changed)
        self.filter_frames["instruments"] = InstrumentFilterFrame(self.filter_content_area, on_change_callback=self._on_filter_changed)
        self.filter_frames["weekday"] = WeekdayFilterFrame(self.filter_content_area, on_change_callback=self._on_filter_changed)
        self.filter_frames["sessions"] = SessionFilterFrame(self.filter_content_area, on_change_callback=self._on_filter_changed)
        self.filter_frames["hourly"] = HourlyFilterFrame(self.filter_content_area, on_change_callback=self._on_filter_changed)
        self.filter_frames["trade_type"] = TradeTypeFilterFrame(self.filter_content_area, on_change_callback=self._on_filter_changed)
        self.filter_frames["errors"] = ErrorFilterFrame(self.filter_content_area, on_change_callback=self._on_filter_changed)

        self._create_filter_buttons()
        self._show_filter_frame("date_range")
        
        # Initialize dates for DateRangeFilterFrame AFTER all frames are instantiated
        # This will trigger the first _on_filter_changed, which in turn reloads other filters and updates summary.
        self.filter_frames["date_range"].initialize_dates()


        self.generate_report_button = ctk.CTkButton(self.summary_section_frame,
                                                    text=process_persian_text_for_matplotlib("تهیه گزارش"),
                                                    command=self._generate_report,
                                                    font=("Vazirmatn", 14, "bold"),
                                                    fg_color="#007BFF",
                                                    hover_color="#0056B3")
        self.summary_section_frame.grid_rowconfigure(99, weight=1)
        self.generate_report_button.grid(row=99, column=0, columnspan=2, sticky="s", pady=(10,5))
        
        self.detail_frame = ReportDetailFrame(self.main_frame, fg_color="white", corner_radius=8)
        self.detail_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=0, pady=(10,0))

        self.focus_set()
        self.wait_window(self)

    def _on_filter_changed(self):
        """
        Handles changes in any filter. This is the central point to
        trigger dependent filter reloads and summary updates.
        """
        # همیشه اول بازه تاریخی و نوع ترید رو بگیر چون بقیه بهشون وابسته هستن
        current_date_range = self.filter_frames["date_range"].get_selection()
        current_trade_type_filter = self.filter_frames["trade_type"].get_selection()

        # Reload instruments based on new date range
        self.filter_frames["instruments"].reload_symbols(current_date_range)

        # Reload sessions (now also gets user's timezone for display)
        self.filter_frames["sessions"].reload_sessions()

        # Reload errors based on new date range and trade type
        self.filter_frames["errors"].reload_errors(current_date_range, current_trade_type_filter)

        # Then update the summary for all filters
        self._update_filter_summary()


    def _create_filter_buttons(self):
        button_texts = [
            ("date_range", "بازه تاریخی"),
            ("instruments", "نمادها"),
            ("weekday", "روزهای هفته"),
            ("sessions", "سشن‌های معاملاتی"),
            ("hourly", "ساعات ترید"),
            ("trade_type", "نوع ترید"),
            ("errors", "اشتباهات")
        ]
        
        base_colors = [
            "#007BFF", "#28A745", "#FFC107", "#6F42C1", "#DC3545", "#17A2B8", "#6C757D"
        ]
        
        for i, (key, text) in enumerate(button_texts):
            button_color = base_colors[i % len(base_colors)]
            button = ctk.CTkButton(self.filter_buttons_frame,
                                   text=process_persian_text_for_matplotlib(text),
                                   command=lambda k=key: self._show_filter_frame(k),
                                   font=("Vazirmatn", 13, "bold"),
                                   fg_color=button_color,
                                   text_color="white",
                                   hover_color=self._darken_color(button_color, 20),
                                   corner_radius=8,
                                   height=40,
                                   width=140)
            button.grid(row=i, column=0, sticky="ew", pady=3, padx=5)
            self.filter_buttons[key] = button

    def _darken_color(self, hex_color, percent):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darker_rgb = tuple(max(0, c - int(c * percent / 100)) for c in rgb)
        return '#%02x%02x%02x' % darker_rgb

    def _get_original_button_color(self, key):
        base_colors = [
            "#007BFF", "#28A745", "#FFC107", "#6F42C1", "#DC3545", "#17A2B8", "#6C757D"
        ]
        button_keys_order = ["date_range", "instruments", "weekday", "sessions", "hourly", "trade_type", "errors"]
        try:
            index = button_keys_order.index(key)
            return base_colors[index % len(base_colors)]
        except ValueError:
            return "#6C757D"

    def _show_filter_frame(self, key):
        if self.active_filter_frame:
            self.active_filter_frame.grid_forget()
        
        self.active_filter_frame = self.filter_frames[key]
        self.active_filter_frame.grid(row=0, column=0, sticky="nsew")

        for k, button in self.filter_buttons.items():
            if k == key:
                original_color = self._get_original_button_color(k)
                button.configure(fg_color=self._darken_color(original_color, 15))
                button.configure(text_color="white")
            else:
                button.configure(fg_color=self._get_original_button_color(k))
                button.configure(text_color="white")

        self._update_filter_summary()

    def _update_filter_summary(self):
        # Clear previous summary entries
        for widget in self.summary_table_frame.winfo_children():
            widget.destroy()

        summary_data = []
        
        all_filters_data = {}
        # Ensure all filter frames are properly initialized before attempting to get their selections.
        for key in ["date_range", "instruments", "weekday", "sessions", "hourly", "trade_type", "errors"]:
            if key in self.filter_frames: # Check if key exists in filter_frames dict
                all_filters_data[key] = self.filter_frames[key].get_selection()
            else:
                all_filters_data[key] = "خطا در بارگذاری"

        summary_data.append((process_persian_text_for_matplotlib('بازه تاریخی:'), f"{process_persian_text_for_matplotlib(all_filters_data['date_range']['start_date'])} {process_persian_text_for_matplotlib('تا')} {process_persian_text_for_matplotlib(all_filters_data['date_range']['end_date'])}"))

        selected_instruments = all_filters_data['instruments']
        if isinstance(selected_instruments, list):
            if selected_instruments:
                summary_data.append((process_persian_text_for_matplotlib('نمادها:'), process_persian_text_for_matplotlib(', '.join(selected_instruments))))
            else:
                summary_data.append((process_persian_text_for_matplotlib('نمادها:'), process_persian_text_for_matplotlib('هیچکدام')))
        else: # "همه"
            summary_data.append((process_persian_text_for_matplotlib('نمادها:'), process_persian_text_for_matplotlib('همه')))
            
        selected_weekdays = all_filters_data['weekday']
        if isinstance(selected_weekdays, list):
            if selected_weekdays:
                weekday_names_map = {
                    0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنج‌شنبه", 4: "جمعه", 5: "شنبه", 6: "یکشنبه"
                }
                display_weekdays = [weekday_names_map.get(idx, str(idx)) for idx in sorted(selected_weekdays)]
                summary_data.append((process_persian_text_for_matplotlib('روزهای هفته:'), process_persian_text_for_matplotlib(', '.join(display_weekdays))))
            else:
                summary_data.append((process_persian_text_for_matplotlib('روزهای هفته:'), process_persian_text_for_matplotlib('هیچکدام')))
        else: # "همه"
            summary_data.append((process_persian_text_for_matplotlib('روزهای هفته:'), process_persian_text_for_matplotlib(selected_weekdays)))

        # Start of changed block for sessions
        selected_sessions = all_filters_data['sessions']
        if isinstance(selected_sessions, list):
            if selected_sessions:
                # استفاده از session_names_map و db_manager برای دریافت اطلاعات کامل‌تر
                # db_manager.get_session_times_with_display_utc نیاز به user_timezone_name داره
                # اما چون اینجا فقط برای نمایش متنه، میتونیم از نقشه اسمی session_filter استفاده کنیم
                session_filter_instance = self.filter_frames["sessions"]
                display_sessions_texts = []
                # اینجا نیاز داریم اطلاعات زمان‌های نمایش رو از شیء SessionFilterFrame بگیریم
                # به جای اینکه دوباره از db_manager بخونیم که ممکنه سنگین باشه
                # یا اطلاعات دقیق‌تر رو از خود SessionFilterFrame بگیریم.
                # بهتره اطلاعات نمایش رو خود SessionFilterFrame برگردونه.

                # با توجه به اینکه session_filter.py تغییر کرده تا get_selection
                # فقط کلیدهای سشن رو برگردونه، برای نمایش کامل، باید از
                # `db_manager.get_session_times_with_display_utc` استفاده کنیم
                # یا `session_filter.py` یک متد جدید برای `get_display_selection` داشته باشه.
                # برای این اصلاح، فرض می‌کنیم get_session_times_with_display_utc رو صدا می‌زنیم
                # تا اطلاعات نمایش رو بگیریم.
                import db_manager # Added import for db_manager
                user_tz = db_manager.get_default_timezone()
                all_session_details = db_manager.get_session_times_with_display_utc(user_tz)

                for key in selected_sessions:
                    details = all_session_details.get(key)
                    if details:
                        session_display_name = session_filter_instance.session_names_map.get(key, key.capitalize())
                        display_sessions_texts.append(f"{session_display_name} ({details['start_display']} - {details['end_display']})")
                summary_data.append((process_persian_text_for_matplotlib('سشن‌ها:'), process_persian_text_for_matplotlib(', '.join(display_sessions_texts))))
            else:
                summary_data.append((process_persian_text_for_matplotlib('سشن‌ها:'), process_persian_text_for_matplotlib('هیچکدام')))
        else: # "همه"
            summary_data.append((process_persian_text_for_matplotlib('سشن‌ها:'), process_persian_text_for_matplotlib(selected_sessions)))
        # End of changed block for sessions

        # Update summary for trade_type
        summary_data.append((process_persian_text_for_matplotlib('نوع ترید:'), process_persian_text_for_matplotlib(all_filters_data['trade_type'])))
        
        # Update summary for errors
        selected_errors = all_filters_data['errors']
        if isinstance(selected_errors, list):
            if selected_errors:
                summary_data.append((process_persian_text_for_matplotlib('اشتباهات:'), process_persian_text_for_matplotlib(', '.join(selected_errors))))
            else:
                summary_data.append((process_persian_text_for_matplotlib('اشتباهات:'), process_persian_text_for_matplotlib('هیچکدام')))
        else: # "همه"
            summary_data.append((process_persian_text_for_matplotlib('اشتباهات:'), process_persian_text_for_matplotlib(selected_errors)))

        summary_data.append((process_persian_text_for_matplotlib('ساعات روز:'), process_persian_text_for_matplotlib(all_filters_data['hourly'])))


        # Populate the summary_table_frame
        for r, (caption, value) in enumerate(summary_data):
            caption_label = ctk.CTkLabel(self.summary_table_frame, text=caption,
                                         font=("Vazirmatn", 12), text_color="#424242", anchor='e')
            caption_label.grid(row=r, column=1, sticky='e', padx=2, pady=1)

            value_label = ctk.CTkLabel(self.summary_table_frame, text=value,
                                       font=("Vazirmatn", 12, "bold"), text_color="#212121", anchor='e', wraplength=int(self.winfo_width() * 0.2))
            value_label.grid(row=r, column=0, sticky='e', padx=2, pady=1)


    def _generate_report(self):
        filters = {}
        
        date_range_selection = self.filter_frames["date_range"].get_selection()
        if date_range_selection:
            try:
                start_date_obj = datetime.strptime(date_range_selection["start_date"], '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(date_range_selection["end_date"], '%Y-%m-%d').date()
                if start_date_obj > end_date_obj:
                    messagebox.showwarning(process_persian_text_for_matplotlib("خطا در تاریخ"),
                                           process_persian_text_for_matplotlib("تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد."))
                    return
                filters["date_range"] = date_range_selection
            except ValueError:
                messagebox.showerror(process_persian_text_for_matplotlib("خطا در تاریخ"),
                                      process_persian_text_for_matplotlib("فرمت تاریخ نامعتبر است. لطفاً از فرمت YYYY-MM-DD استفاده کنید."))
                return

        instrument_selection = self.filter_frames["instruments"].get_selection()
        if isinstance(instrument_selection, list) and not instrument_selection:
             messagebox.showwarning(process_persian_text_for_matplotlib("انتخاب نماد"),
                                    process_persian_text_for_matplotlib("لطفاً حداقل یک نماد را انتخاب کنید."))
             return
        filters["instruments"] = instrument_selection

        filters["sessions"] = self.filter_frames["sessions"].get_selection()
        filters["trade_type"] = self.filter_frames["trade_type"].get_selection()
        filters["errors"] = self.filter_frames["errors"].get_selection()
        filters["hourly"] = self.filter_frames["hourly"].get_selection()
        filters["weekday"] = self.filter_frames["weekday"].get_selection()


        self.detail_frame.update_report(filters)


def show_report_selection_window(parent_root, open_toplevel_windows_list):
    ReportSelectionWindow(parent_root, open_toplevel_windows_list)

# برای تست مستقل (فقط برای توسعه)
if __name__ == "__main__":
    class MockDBManager:
        def get_unique_symbols(self, start_date=None, end_date=None): # Updated signature
            if start_date and end_date:
                # Mock filtering based on date range
                print(f"Mock DB: Getting symbols for {start_date} to {end_date}")
                if start_date >= "2024-07-01":
                    return ["USDCAD", "EURCAD"]
                else:
                    return ["US30", "XAUUSD", "EURUSD", "GBPUSD", "NZDUSD", "AUDCAD"]
            return ["US30", "XAUUSD", "EURUSD", "GBPUSD", "NZDUSD", "AUDCAD"]
        def get_first_trade_date(self):
            return "2023-01-01"
        def get_working_days(self):
            return [0, 1, 2, 3, 4] # Monday-Friday
        def get_session_times_utc(self):
            return {
                'ny': {'start': '13:30', 'end': '20:00'},
                'london': {'start': '07:00', 'end': '15:30'},
                'sydney': {'start': '00:00', 'end': '06:00'},
                'tokyo': {'start': '00:00', 'end': '06:00'}
            }
        def get_session_times_with_display_utc(self, user_timezone_name): # Added
            # یک پیاده‌سازی mock ساده برای تست
            # در اینجا فرض می‌کنیم Asia/Tehran کاربره
            mock_sessions = {
                'ny': {'start_utc': '13:30', 'end_utc': '20:00', 'start_display': '17:00', 'end_display': '23:30'}, # مثال برای Asia/Tehran (+3:30)
                'sydney': {'start_utc': '00:00', 'end_utc': '06:00', 'start_display': '03:30', 'end_display': '09:30'},
                'tokyo': {'start_utc': '00:00', 'end_utc': '06:00', 'start_display': '03:30', 'end_display': '09:30'},
                'london': {'start_utc': '07:00', 'end_utc': '15:30', 'start_display': '10:30', 'end_display': '19:00'} # مثال برای Asia/Tehran (+3:30)
            }
            return mock_sessions
        def get_trades_by_filters(self, filters):
            print(f"Mock DB: Fetching trades with filters: {filters}")
            return []
        def get_unique_errors_by_filters(self, start_date=None, end_date=None, trade_type_filter=None): # Added
            print(f"Mock DB: Getting errors for date range {start_date}-{end_date} and trade type {trade_type_filter}")
            if start_date and start_date < "2024-01-01":
                return ["اشتباه حجم زیاد", "ورود زودهنگام", "نداشتن حد ضرر"]
            return ["اشتباه حجم زیاد", "ورود زودهنگام"]
        def get_default_timezone(self): # Added mock for get_default_timezone
            return "Asia/Tehran"


    import db_manager as original_db_manager
    original_db_manager.get_unique_symbols = MockDBManager().get_unique_symbols
    original_db_manager.get_first_trade_date = MockDBManager().get_first_trade_date
    original_db_manager.get_working_days = MockDBManager().get_working_days
    original_db_manager.get_session_times_utc = MockDBManager().get_session_times_utc
    original_db_manager.get_session_times_with_display_utc = MockDBManager().get_session_times_with_display_utc
    original_db_manager.get_trades_by_filters = MockDBManager().get_trades_by_filters
    original_db_manager.get_unique_errors_by_filters = MockDBManager().get_unique_errors_by_filters
    original_db_manager.get_default_timezone = MockDBManager().get_default_timezone # Set mock


    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root_test = ctk.CTk()
    root_test.withdraw()

    mock_open_windows = []
    show_report_selection_window(root_test, mock_open_windows)
    root_test.mainloop()