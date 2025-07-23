# report_filters/date_range_filter.py

import customtkinter as ctk
from datetime import datetime, timedelta
import tkcalendar as tkc
import tkinter as tk
from persian_chart_utils import process_persian_text_for_matplotlib
import db_manager


class DateRangeFilterFrame(ctk.CTkFrame):
    def __init__(self, master, on_change_callback=None, fg_color="transparent", **kwargs):
        super().__init__(master, fg_color=fg_color, **kwargs)
        self.on_change_callback = on_change_callback
        
        # Grid Configuration for Inputs and Quick Filters
        self.grid_columnconfigure(0, weight=1) # Left column for entries
        self.grid_columnconfigure(1, weight=1) # Right column for labels

        # Input Fields for Custom Date Range
        self.start_date_label = ctk.CTkLabel(self, text="From:", font=("Vazirmatn", 12))
        self.start_date_label.grid(row=0, column=1, padx=5, pady=5, sticky="e")
        
        self.start_date_entry = tkc.DateEntry(self, selectmode='day',
                                                    date_pattern='yyyy-mm-dd',
                                                    locale='en_US',
                                                    font=("Vazirmatn", 10),
                                                    background='#2B2B2B' if ctk.get_appearance_mode() == "Dark" else '#EBEBEB',
                                                    foreground='#FFFFFF' if ctk.get_appearance_mode() == "Dark" else '#000000',
                                                    bordercolor='#3B8ED0' if ctk.get_appearance_mode() == "Dark" else '#3B8ED0',
                                                    headersbackground='#3B8ED0' if ctk.get_appearance_mode() == "Dark" else '#3B8ED0',
                                                    headersforeground='white',
                                                    selectbackground='#1F6AA5' if ctk.get_appearance_mode() == "Dark" else '#1F6AA5',
                                                    selectforeground='white',
                                                    weekendbackground='#424242' if ctk.get_appearance_mode() == "Dark" else '#DDDDDD',
                                                    weekendforeground='#FFFFFF' if ctk.get_appearance_mode() == "Dark" else '#000000',
                                                    normalbackground=ctk.ThemeManager.theme["CTkEntry"]["fg_color"][0] if ctk.get_appearance_mode() == "Light" else ctk.ThemeManager.theme["CTkEntry"]["fg_color"][1],
                                                    normalforeground=ctk.ThemeManager.theme["CTkEntry"]["text_color"][0] if ctk.get_appearance_mode() == "Light" else ctk.ThemeManager.theme["CTkEntry"]["text_color"][1],
                                                    borderwidth=2
                                                    )
        self.start_date_entry.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.start_date_entry.set_date((datetime.now() - timedelta(days=30)).date())
        self.start_date_entry.bind("<<DateEntrySelected>>", lambda e: self._on_date_selected(e, update_preset=True))


        self.end_date_label = ctk.CTkLabel(self, text="To:", font=("Vazirmatn", 12))
        self.end_date_label.grid(row=1, column=1, padx=5, pady=5, sticky="e")
        
        self.end_date_entry = tkc.DateEntry(self, selectmode='day',
                                                  date_pattern='yyyy-mm-dd',
                                                  locale='en_US',
                                                  font=("Vazirmatn", 10),
                                                  background='#2B2B2B' if ctk.get_appearance_mode() == "Dark" else '#EBEBEB',
                                                  foreground='#FFFFFF' if ctk.get_appearance_mode() == "Dark" else '#000000',
                                                  bordercolor='#3B8ED0' if ctk.get_appearance_mode() == "Dark" else '#3B8ED0',
                                                  headersbackground='#3B8ED0' if ctk.get_appearance_mode() == "Dark" else '#3B8ED0',
                                                  headersforeground='white',
                                                  selectbackground='#1F6AA5' if ctk.get_appearance_mode() == "Dark" else '#1F6AA5',
                                                  selectforeground='white',
                                                  weekendbackground='#424242' if ctk.get_appearance_mode() == "Dark" else '#DDDDDD',
                                                  weekendforeground='#FFFFFF' if ctk.get_appearance_mode() == "Dark" else '#000000',
                                                  normalbackground=ctk.ThemeManager.theme["CTkEntry"]["fg_color"][0] if ctk.get_appearance_mode() == "Light" else ctk.ThemeManager.theme["CTkEntry"]["fg_color"][1],
                                                  normalforeground=ctk.ThemeManager.theme["CTkEntry"]["text_color"][0] if ctk.get_appearance_mode() == "Light" else ctk.ThemeManager.theme["CTkEntry"]["text_color"][1],
                                                  borderwidth=2
                                                  )
        self.end_date_entry.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.end_date_entry.set_date(datetime.now().date())
        self.end_date_entry.bind("<<DateEntrySelected>>", lambda e: self._on_date_selected(e, update_preset=True))

        # Quick Filter Buttons
        self.quick_filter_label = ctk.CTkLabel(self, text=process_persian_text_for_matplotlib("انتخاب سریع:"), font=("Vazirmatn", 12))
        self.quick_filter_label.grid(row=2, column=1, padx=5, pady=(15,5), sticky="e")

        self.quick_filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.quick_filter_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        self.quick_filter_frame.grid_columnconfigure((0,1), weight=1)

        self.current_selection_var = tk.StringVar(value="custom")

        quick_filter_options = [
            ("امروز", "today", self._set_today),
            ("سه روز اخیر", "last_3_days", self._set_last_n_days(3)),
            ("هفته اخیر", "last_week", self._set_last_n_days(7)),
            ("ماه اخیر", "last_30_days", self._set_last_n_days(30)), # Changed to 30 days
            ("سه ماه اخیر", "last_90_days", self._set_last_n_days(90)), # Changed to 90 days
            ("شش ماه اخیر", "last_180_days", self._set_last_n_days(180)), # Changed to 180 days
            ("کل بازه زمانی تریدها", "all_time", self._set_all_time)
        ]

        self.radio_buttons = []
        for i, (text, value, command) in enumerate(quick_filter_options):
            radio_button = ctk.CTkRadioButton(self.quick_filter_frame,
                                              text=process_persian_text_for_matplotlib(text),
                                              variable=self.current_selection_var,
                                              value=value,
                                              command=command,
                                              font=("Vazirmatn", 11),
                                              radiobutton_width=20,
                                              radiobutton_height=20,
                                              border_width_checked=6,
                                              border_color="#3B8ED0",
                                              fg_color="#3B8ED0",
                                              hover_color="#1F6AA5",
                                              text_color_disabled="gray50")
            row_num = i // 2
            col_num = i % 2
            radio_button.grid(row=row_num, column=col_num, padx=5, pady=5, sticky="ew")
            self.radio_buttons.append(radio_button)

        # Removed _set_initial_dates() from here. It will be called externally.

    def initialize_dates(self):
        """Called externally by the main report window to set initial date preset."""
        # Set default to "last_month" (which is now last_30_days)
        self.current_selection_var.set("last_30_days")
        self._set_last_n_days(30)() # Directly call the command function
        # This will trigger the on_change_callback, which is desired.

    def _on_date_selected(self, event=None, update_preset=True):
        if update_preset:
            self.current_selection_var.set("custom")
        
        if self.on_change_callback:
            self.on_change_callback()

    def _set_today(self):
        today = datetime.now().date()
        self.start_date_entry.set_date(today)
        self.end_date_entry.set_date(today)
        self.current_selection_var.set("today")
        if self.on_change_callback:
            self.on_change_callback()

    def _set_last_n_days(self, n_days):
        def _command():
            today = datetime.now().date()
            start_date = today - timedelta(days=n_days - 1)
            self.start_date_entry.set_date(start_date)
            self.end_date_entry.set_date(today)
            self.current_selection_var.set(f"last_{n_days}_days") # Adjusted value to reflect days
            if self.on_change_callback:
                self.on_change_callback()
        return _command

    def _set_last_n_months(self, n_months):
        # This method is no longer directly used by quick filter options
        # as we are now using _set_last_n_days(XX) for all presets
        # but kept for potential future use or if a true "month" logic is needed
        def _command():
            today = datetime.now().date()
            # Calculate start date by subtracting months, then adjusting to first day of that month
            year = today.year
            month = today.month
            
            target_month = month - n_months
            target_year = year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            
            start_date = today.replace(year=target_year, month=target_month, day=1)
            self.start_date_entry.set_date(start_date)
            self.end_date_entry.set_date(today)
            self.current_selection_var.set(f"last_{n_months}_months_start") # Adjusted value
            if self.on_change_callback:
                self.on_change_callback()
        return _command

    def _set_all_time(self):
        first_trade_date_str = db_manager.get_first_trade_date()
        
        if first_trade_date_str:
            first_trade_date_obj = datetime.strptime(first_trade_date_str, '%Y-%m-%d').date()
            self.start_date_entry.set_date(first_trade_date_obj)
        else:
            self.start_date_entry.set_date(datetime(2000, 1, 1).date()) # Fallback to a very old date

        self.end_date_entry.set_date(datetime.now().date())
        self.current_selection_var.set("all_time")
        if self.on_change_callback:
            self.on_change_callback()

    def get_selection(self):
        start_date = self.start_date_entry.get_date().strftime('%Y-%m-%d')
        end_date = self.end_date_entry.get_date().strftime('%Y-%m-%d')
        return {"start_date": start_date, "end_date": end_date, "preset": self.current_selection_var.get()}

    def set_selection(self, start_date_str, end_date_str, preset="custom"):
        try:
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            self.start_date_entry.set_date(start_date_obj)
            self.end_date_entry.set_date(end_date_obj)
            self.current_selection_var.set(preset)
        except ValueError:
            print("Invalid date format provided to set_selection in DateRangeFilterFrame.")
            self.current_selection_var.set("custom")