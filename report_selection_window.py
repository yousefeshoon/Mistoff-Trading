# report_selection_window.py

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog
import os
import sys
from datetime import datetime, timedelta
from tkinter import ttk

# Import all modular filter frames
from report_filters import (
    DateRangeFilterFrame,
    InstrumentFilterFrame,
    SessionFilterFrame,
    TradeTypeFilterFrame,
    ErrorFilterFrame,
    HourlyFilterFrame,
    WeekdayFilterFrame
)
# import report_detail_frame.py # <<< حذف شده
# Import Persian text utility
from persian_chart_utils import process_persian_text_for_matplotlib, set_titlebar_text
import db_manager
import json

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
        self.is_editing_template = False # Flag for edit mode
        self.original_filters_before_edit = {} # To store filters before editing a template
        self.editing_template_id = None # Store the ID of the template being edited

        def on_close():
            if self in self.open_toplevel_windows_list:
                self.open_toplevel_windows_list.remove(self)

            for filter_key in self.filter_frames:
                if hasattr(self.filter_frames[filter_key], 'on_change_callback'):
                    self.filter_frames[filter_key].on_change_callback = None

            self.destroy()

        self.protocol("WM_DELETE_WINDOW", on_close)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # افزایش عرض پنجره برای جا شدن دکمه‌ها و محتوا
        win_width = int(screen_width * 0.8)
        win_height = int(screen_height * 0.8)

        x = (screen_width / 2) - (win_width / 2)
        y = (screen_height / 2) - (win_height / 2)

        self.geometry(f'{win_width}x{win_height}+{int(x)}+{int(y)}')
        self.configure(fg_color="#F0F2F5") # Light gray background for the window

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=0) # Header
        #self.main_frame.grid_rowconfigure(1, weight=1) # Filler space (was detail_frame)
        self.main_frame.grid_rowconfigure(1, weight=1) # Footer

        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=8)
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.header_frame.grid_columnconfigure(0, weight=0, minsize=int(win_width * 0.3))
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

        self.filters_main_container.grid_columnconfigure(0, weight=1)
        self.filters_main_container.grid_columnconfigure(1, weight=0, minsize=150)

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
        self.filter_frames["date_range"] = DateRangeFilterFrame(self.filter_content_area, on_change_callback=self._on_filter_changed)
        self.filter_frames["instruments"] = InstrumentFilterFrame(self.filter_content_area, on_change_callback=self._on_filter_changed)
        self.filter_frames["weekday"] = WeekdayFilterFrame(self.filter_content_area, on_change_callback=self._on_filter_changed)
        self.filter_frames["sessions"] = SessionFilterFrame(self.filter_content_area, on_change_callback=self._on_filter_changed)
        self.filter_frames["hourly"] = HourlyFilterFrame(self.filter_content_area, on_change_callback=self._on_filter_changed)
        self.filter_frames["trade_type"] = TradeTypeFilterFrame(self.filter_content_area, on_change_callback=self._on_filter_changed)
        self.filter_frames["errors"] = ErrorFilterFrame(self.filter_content_area, on_change_callback=self._on_filter_changed)

        self._create_filter_buttons()

        # دکمه ذخیره قالب گزارش - منتقل شده به هدر، زیر ستون خلاصه فیلترها
        self.template_actions_frame = ctk.CTkFrame(self.filters_main_container, fg_color="transparent")
        self.template_actions_frame.grid(row=1, column=0, columnspan=2, padx=0, pady=(10, 0), sticky="ew") # Changed grid to cover both filter columns
        self.template_actions_frame.grid_columnconfigure(0, weight=1) # For save button
        self.template_actions_frame.grid_columnconfigure(1, weight=1) # For reset/cancel button

        self.save_template_button = ctk.CTkButton(self.template_actions_frame,
                                                    text=process_persian_text_for_matplotlib("ذخیره قالب گزارش"),
                                                    command=self._save_report_template,
                                                    font=("Vazirmatn", 12),
                                                    fg_color="#007BFF",
                                                    hover_color="#0056B3")
        self.save_template_button.grid(row=0, column=0, padx=(10, 5), pady=(0, 0), sticky="ew")

        self.reset_cancel_button = ctk.CTkButton(self.template_actions_frame,
                                                    text=process_persian_text_for_matplotlib("ریست فیلترها"),
                                                    command=self._reset_filters,
                                                    font=("Vazirmatn", 12),
                                                    fg_color="#6C757D",
                                                    hover_color="#5A6268")
        self.reset_cancel_button.grid(row=0, column=1, padx=(5, 10), pady=(0, 0), sticky="ew")


        # Placeholder frame where report detail (charts) used to be. Now just a filler.
        #self.filler_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent") # Was self.detail_frame
        #self.filler_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(10,0))
        # Add a label to indicate this area is empty or for future use
        #self.filler_label = ctk.CTkLabel(self.filler_frame, text=process_persian_text_for_matplotlib("این قسمت در آینده برای نمایش جزئیات گزارش استفاده خواهد شد."),
        #                                     font=("Vazirmatn", 14), text_color="gray", wraplength=400, justify="right")
        #self.filler_label.pack(expand=True)


        # --- Footer Frame for Report Templates ---
        self.footer_frame = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=8)
        self.footer_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(10, 0))
        self.footer_frame.grid_columnconfigure(0, weight=1)
        self.footer_frame.grid_rowconfigure(0, weight=0) # For templates title and buttons
        self.footer_frame.grid_rowconfigure(1, weight=1, minsize=100) # For Treeview
        self.footer_frame.grid_propagate(False)

        # Container for Templates Label and Buttons
        self.templates_header_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        self.templates_header_frame.grid(row=0, column=0, padx=10, pady=(10,5), sticky="ew")
        self.templates_header_frame.grid_columnconfigure(0, weight=1) # For label
        self.templates_header_frame.grid_columnconfigure(1, weight=2) # For buttons

        self.templates_label = ctk.CTkLabel(self.templates_header_frame, text=process_persian_text_for_matplotlib("قالب‌های گزارش ذخیره شده:"),
                                            font=("Vazirmatn", 14, "bold"), text_color="#202124")
        self.templates_label.grid(row=0, column=0, sticky="e")

        self.template_buttons_row_frame = ctk.CTkFrame(self.templates_header_frame, fg_color="transparent")
        self.template_buttons_row_frame.grid(row=0, column=1, sticky="e", padx=(10,0))
        for i in range(5): # 5 buttons
            self.template_buttons_row_frame.grid_columnconfigure(i, weight=1)

        self.delete_template_button = ctk.CTkButton(self.template_buttons_row_frame,
                                                    text=process_persian_text_for_matplotlib("حذف قالب"),
                                                    command=self._delete_template,
                                                    font=("Vazirmatn", 12), fg_color="#DC3545", hover_color="#C82333",
                                                    state="disabled")
        self.delete_template_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.edit_template_name_button = ctk.CTkButton(self.template_buttons_row_frame, # Renamed variable for clarity
                                                text=process_persian_text_for_matplotlib("ویرایش نام"),
                                                command=self._edit_template_name,
                                                font=("Vazirmatn", 12), fg_color="#FFC107", hover_color="#E0A800",
                                                state="disabled")
        self.edit_template_name_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.copy_template_button = ctk.CTkButton(self.template_buttons_row_frame,
                                                    text=process_persian_text_for_matplotlib("کپی از قالب"),
                                                    command=self._copy_template,
                                                    font=("Vazirmatn", 12), fg_color="#17A2B8", hover_color="#138496",
                                                    state="disabled")
        self.copy_template_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        self.edit_template_button = ctk.CTkButton(self.template_buttons_row_frame, # This button now means "Load for Edit"
                                                text=process_persian_text_for_matplotlib("ویرایش قالب"),
                                                command=self._edit_selected_template,
                                                font=("Vazirmatn", 12), fg_color="#28A745", hover_color="#218838",
                                                state="disabled")
        self.edit_template_button.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        
        self.generate_report_button = ctk.CTkButton(self.template_buttons_row_frame,
                                                    text=process_persian_text_for_matplotlib("تهیه گزارش"), # From selected template
                                                    command=self._generate_report_from_template,
                                                    font=("Vazirmatn", 12),
                                                    fg_color="#007BFF",
                                                    hover_color="#0056B3",
                                                    state="disabled")
        self.generate_report_button.grid(row=0, column=4, padx=5, pady=5, sticky="ew")

        # Treeview for saved templates
        template_tree_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        template_tree_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        template_tree_frame.grid_columnconfigure(0, weight=1)
        template_tree_frame.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Treeview",
                        background=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][0] if ctk.get_appearance_mode() == "Light" else "#2B2B2B",
                        foreground=ctk.ThemeManager.theme["CTkLabel"]["text_color"][0] if ctk.get_appearance_mode() == "Light" else "white",
                        fieldbackground=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][0] if ctk.get_appearance_mode() == "Light" else "#2B2B2B",
                        rowheight=30,
                        borderwidth=0,
                        highlightthickness=0,
                        font=("Vazirmatn", 11))

        style.map('Treeview',
                  background=[('selected', '#3B8ED0')],
                  foreground=[('selected', 'white')])

        style.configure("Treeview.Heading",
                        font=("Vazirmatn", 11, "bold"),
                        background="#007BFF",
                        foreground="white",
                        padding=[10, 5],
                        relief="flat")
        style.map("Treeview.Heading",
                  background=[('active', '#0056B3')])

        style.configure("TemplateName.Treeview", font=("Vazirmatn", 13, "bold"))

        self.templates_tree = ttk.Treeview(template_tree_frame, columns=("ID", "Name"), show="headings")
        self.templates_tree.heading("ID", text="ID")
        self.templates_tree.heading("Name", text=process_persian_text_for_matplotlib("نام قالب"))
        self.templates_tree.column("ID", width=50, stretch=tk.NO, anchor='center')
        self.templates_tree.column("Name", stretch=tk.YES, anchor='e')

        self.templates_tree.pack(fill=tk.BOTH, expand=True)

        templates_scrollbar = ctk.CTkScrollbar(template_tree_frame, command=self.templates_tree.yview)
        templates_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.templates_tree.configure(yscrollcommand=templates_scrollbar.set)

        self.templates_tree.bind("<<TreeviewSelect>>", self._on_template_selected)

        # --- نقطه کلیدی: فراخوانی update_idletasks() بعد از ساخت و چیدمان اولیه ---
        self.update_idletasks()

        self._show_filter_frame("date_range")
        self.filter_frames["date_range"].initialize_dates()
        self._populate_templates_list()
        self._reset_edit_mode_ui() # Initialize button states

        self.focus_set()
        self.wait_window(self)

    def _on_filter_changed(self):
        """
        Handles changes in any filter. This is the central point to
        trigger dependent filter reloads and summary updates.
        """
        current_date_range = self.filter_frames["date_range"].get_selection()
        current_trade_type_filter = self.filter_frames["trade_type"].get_selection()
        current_session_filter_selection = self.filter_frames["sessions"].get_selection()

        # Reload instruments based on new date range
        self.filter_frames["instruments"].reload_symbols(current_date_range)

        # Reload sessions (now also gets user's timezone for display)
        self.filter_frames["sessions"].reload_sessions()

        # Reload errors based on new date range and trade type
        self.filter_frames["errors"].reload_errors(current_date_range, current_trade_type_filter)

        # Reload hourly filter based on selected sessions
        self.filter_frames["hourly"].reload_hourly_data(selected_sessions_from_main=current_session_filter_selection)

        # Then update the summary for all filters
        self._update_filter_summary()
        # Reset template selection when filters are changed manually
        self._clear_template_selection()
        # Exit edit mode if filters are changed manually
        # این قسمت رو حذف کن:
        # if self.is_editing_template:
        #     self.is_editing_template = False
        #     self.editing_template_id = None
        #     self._reset_edit_mode_ui()

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

    def _lighten_color(self, hex_color, percent):
        """
        Lightens a given hex color by a specified percentage.
        Returns the lighter color as a hex string.
        """
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        lighter_rgb = tuple(min(255, c + int((255 - c) * percent / 100)) for c in rgb)
        return '#%02x%02x%02x' % lighter_rgb

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
        self._clear_template_selection() # Clear selection if user manually switches tabs

    def _update_filter_summary(self):
        for widget in self.summary_table_frame.winfo_children():
            widget.destroy()

        summary_display_limit = 4 # Max number of buttons before 'و...'
        current_row = 0

        # Define button colors for each filter category
        # These are lightened versions of the main filter buttons
        button_category_colors = {
            "date_range": self._lighten_color("#007BFF", 85), # Blue-ish for Date Range
            "instruments": self._lighten_color("#28A745", 85), # Green-ish for Instruments
            "weekday": self._lighten_color("#FFC107", 85),    # Yellow-ish for Weekday
            "sessions": self._lighten_color("#6F42C1", 85),   # Purple-ish for Sessions
            "hourly": self._lighten_color("#DC3545", 85),     # Red-ish for Hourly
            "trade_type": self._lighten_color("#17A2B8", 85), # Cyan-ish for Trade Type
            "errors": self._lighten_color("#6C757D", 85)      # Gray-ish for Errors
        }
        
        button_text_color = "#212121" # Dark text for light buttons

        all_filters_data = {}
        for key in ["date_range", "instruments", "weekday", "sessions", "hourly", "trade_type", "errors"]:
            if key in self.filter_frames:
                all_filters_data[key] = self.filter_frames[key].get_selection()
            else:
                all_filters_data[key] = "خطا در بارگذاری"

        # --- Date Range ---
        date_range_selection = all_filters_data['date_range']
        date_label = ctk.CTkLabel(self.summary_table_frame, text=process_persian_text_for_matplotlib('بازه تاریخی:'),
                                 font=("Vazirmatn", 12), text_color="#424242", anchor='e')
        date_label.grid(row=current_row, column=1, sticky='e', padx=2, pady=1)

        date_value_frame = ctk.CTkFrame(self.summary_table_frame, fg_color="transparent")
        date_value_frame.grid(row=current_row, column=0, sticky='ew', padx=2, pady=1)
        date_value_frame.grid_columnconfigure(0, weight=1) # To center buttons if only one

        date_items = [
            process_persian_text_for_matplotlib(date_range_selection['start_date']),
            process_persian_text_for_matplotlib('تا'),
            process_persian_text_for_matplotlib(date_range_selection['end_date'])
        ]
        
        # Adjust layout for date buttons. Since it's fixed (from/to), no 'و...' needed.
        # We'll use a nested frame for the buttons to control their alignment within column 0.
        inner_date_buttons_frame = ctk.CTkFrame(date_value_frame, fg_color="transparent")
        inner_date_buttons_frame.pack(side="right", anchor="e") # Pack to the right within its cell
        
        # Start Date Button
        ctk.CTkButton(inner_date_buttons_frame,
                        text=date_items[0],
                        font=("Vazirmatn", 11, "bold"),
                        fg_color=button_category_colors["date_range"],
                        text_color=button_text_color,
                        hover_color=button_category_colors["date_range"], # No hover effect for summary buttons
                        corner_radius=15, width=90, height=25).pack(side="right", padx=2)
        
        # 'تا' Label
        ctk.CTkLabel(inner_date_buttons_frame,
                     text=date_items[1],
                     font=("Vazirmatn", 11),
                     text_color=button_text_color).pack(side="right", padx=2)

        # End Date Button
        ctk.CTkButton(inner_date_buttons_frame,
                        text=date_items[2],
                        font=("Vazirmatn", 11, "bold"),
                        fg_color=button_category_colors["date_range"],
                        text_color=button_text_color,
                        hover_color=button_category_colors["date_range"],
                        corner_radius=15, width=90, height=25).pack(side="right", padx=2)
        
        current_row += 1

        # --- Instruments ---
        instrument_label = ctk.CTkLabel(self.summary_table_frame, text=process_persian_text_for_matplotlib('نمادها:'),
                                        font=("Vazirmatn", 12), text_color="#424242", anchor='e')
        instrument_label.grid(row=current_row, column=1, sticky='e', padx=2, pady=1)

        instruments_value_frame = ctk.CTkFrame(self.summary_table_frame, fg_color="transparent")
        instruments_value_frame.grid(row=current_row, column=0, sticky='ew', padx=2, pady=1)
        
        # Use pack for inner buttons, aligned to the right
        inner_instruments_buttons_frame = ctk.CTkFrame(instruments_value_frame, fg_color="transparent")
        inner_instruments_buttons_frame.pack(side="right", anchor="e")

        selected_instruments = all_filters_data['instruments']
        if selected_instruments == "همه":
            ctk.CTkButton(inner_instruments_buttons_frame,
                            text=process_persian_text_for_matplotlib('همه'),
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=button_category_colors["instruments"],
                            text_color=button_text_color,
                            hover_color=button_category_colors["instruments"],
                            corner_radius=15, width=60, height=25).pack(side="right", padx=2)
        elif isinstance(selected_instruments, list) and selected_instruments:
            displayed_count = 0
            for symbol in selected_instruments:
                if displayed_count < summary_display_limit:
                    ctk.CTkButton(inner_instruments_buttons_frame,
                                    text=process_persian_text_for_matplotlib(symbol),
                                    font=("Vazirmatn", 11, "bold"),
                                    fg_color=button_category_colors["instruments"],
                                    text_color=button_text_color,
                                    hover_color=button_category_colors["instruments"],
                                    corner_radius=15, width=70, height=25).pack(side="right", padx=2)
                    displayed_count += 1
                else:
                    ctk.CTkLabel(inner_instruments_buttons_frame,
                                 text=process_persian_text_for_matplotlib(f"و... ({len(selected_instruments) - displayed_count} مورد دیگر)"),
                                 font=("Vazirmatn", 11), text_color=button_text_color).pack(side="right", padx=2)
                    break
        else:
            ctk.CTkButton(inner_instruments_buttons_frame,
                            text=process_persian_text_for_matplotlib('هیچکدام'),
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=button_category_colors["instruments"],
                            text_color=button_text_color,
                            hover_color=button_category_colors["instruments"],
                            corner_radius=15, width=80, height=25).pack(side="right", padx=2)
        current_row += 1

        # --- Weekdays ---
        weekday_label = ctk.CTkLabel(self.summary_table_frame, text=process_persian_text_for_matplotlib('روزهای هفته:'),
                                     font=("Vazirmatn", 12), text_color="#424242", anchor='e')
        weekday_label.grid(row=current_row, column=1, sticky='e', padx=2, pady=1)

        weekday_value_frame = ctk.CTkFrame(self.summary_table_frame, fg_color="transparent")
        weekday_value_frame.grid(row=current_row, column=0, sticky='ew', padx=2, pady=1)

        inner_weekday_buttons_frame = ctk.CTkFrame(weekday_value_frame, fg_color="transparent")
        inner_weekday_buttons_frame.pack(side="right", anchor="e")

        selected_weekdays = all_filters_data['weekday']
        if selected_weekdays == "همه":
            ctk.CTkButton(inner_weekday_buttons_frame,
                            text=process_persian_text_for_matplotlib('همه'),
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=button_category_colors["weekday"],
                            text_color=button_text_color,
                            hover_color=button_category_colors["weekday"],
                            corner_radius=15, width=60, height=25).pack(side="right", padx=2)
        elif isinstance(selected_weekdays, list) and selected_weekdays:
            weekday_names_map = {
                0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنج‌شنبه", 4: "جمعه", 5: "شنبه", 6: "یکشنبه"
            }
            display_weekdays = [weekday_names_map.get(idx, str(idx)) for idx in sorted(selected_weekdays)]
            
            displayed_count = 0
            for day_name in display_weekdays:
                if displayed_count < summary_display_limit:
                    ctk.CTkButton(inner_weekday_buttons_frame,
                                    text=process_persian_text_for_matplotlib(day_name),
                                    font=("Vazirmatn", 11, "bold"),
                                    fg_color=button_category_colors["weekday"],
                                    text_color=button_text_color,
                                    hover_color=button_category_colors["weekday"],
                                    corner_radius=15, width=80, height=25).pack(side="right", padx=2)
                    displayed_count += 1
                else:
                    ctk.CTkLabel(inner_weekday_buttons_frame,
                                 text=process_persian_text_for_matplotlib(f"و... ({len(display_weekdays) - displayed_count} مورد دیگر)"),
                                 font=("Vazirmatn", 11), text_color=button_text_color).pack(side="right", padx=2)
                    break
        else:
             ctk.CTkButton(inner_weekday_buttons_frame,
                            text=process_persian_text_for_matplotlib('هیچکدام'),
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=button_category_colors["weekday"],
                            text_color=button_text_color,
                            hover_color=button_category_colors["weekday"],
                            corner_radius=15, width=80, height=25).pack(side="right", padx=2)
        current_row += 1

        # --- Sessions ---
        session_label = ctk.CTkLabel(self.summary_table_frame, text=process_persian_text_for_matplotlib('سشن‌ها:'),
                                     font=("Vazirmatn", 12), text_color="#424242", anchor='e')
        session_label.grid(row=current_row, column=1, sticky='e', padx=2, pady=1)

        session_value_frame = ctk.CTkFrame(self.summary_table_frame, fg_color="transparent")
        session_value_frame.grid(row=current_row, column=0, sticky='ew', padx=2, pady=1)

        inner_session_buttons_frame = ctk.CTkFrame(session_value_frame, fg_color="transparent")
        inner_session_buttons_frame.pack(side="right", anchor="e")

        selected_sessions = all_filters_data['sessions']
        if selected_sessions == "همه":
            ctk.CTkButton(inner_session_buttons_frame,
                            text=process_persian_text_for_matplotlib('همه'),
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=button_category_colors["sessions"],
                            text_color=button_text_color,
                            hover_color=button_category_colors["sessions"],
                            corner_radius=15, width=60, height=25).pack(side="right", padx=2)
        elif isinstance(selected_sessions, list) and selected_sessions:
            user_tz = db_manager.get_default_timezone()
            all_session_details = db_manager.get_session_times_with_display_utc(user_tz)
            session_filter_instance = self.filter_frames["sessions"] # Access session_names_map
            
            display_sessions_texts = []
            for key in selected_sessions:
                details = all_session_details.get(key)
                if details:
                    session_display_name = session_filter_instance.session_names_map.get(key, key.capitalize())
                    display_sessions_texts.append(f"{session_display_name} ({details['start_display']} - {details['end_display']})")

            displayed_count = 0
            for session_text in display_sessions_texts:
                if displayed_count < summary_display_limit:
                    ctk.CTkButton(inner_session_buttons_frame,
                                    text=process_persian_text_for_matplotlib(session_text),
                                    font=("Vazirmatn", 11, "bold"),
                                    fg_color=button_category_colors["sessions"],
                                    text_color=button_text_color,
                                    hover_color=button_category_colors["sessions"],
                                    corner_radius=15, width=120, height=25).pack(side="right", padx=2)
                    displayed_count += 1
                else:
                    ctk.CTkLabel(inner_session_buttons_frame,
                                 text=process_persian_text_for_matplotlib(f"و... ({len(display_sessions_texts) - displayed_count} مورد دیگر)"),
                                 font=("Vazirmatn", 11), text_color=button_text_color).pack(side="right", padx=2)
                    break
        else:
            ctk.CTkButton(inner_session_buttons_frame,
                            text=process_persian_text_for_matplotlib('هیچکدام'),
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=button_category_colors["sessions"],
                            text_color=button_text_color,
                            hover_color=button_category_colors["sessions"],
                            corner_radius=15, width=80, height=25).pack(side="right", padx=2)
        current_row += 1

        # --- Trade Type ---
        trade_type_label = ctk.CTkLabel(self.summary_table_frame, text=process_persian_text_for_matplotlib('نوع ترید:'),
                                        font=("Vazirmatn", 12), text_color="#424242", anchor='e')
        trade_type_label.grid(row=current_row, column=1, sticky='e', padx=2, pady=1)

        trade_type_value_frame = ctk.CTkFrame(self.summary_table_frame, fg_color="transparent")
        trade_type_value_frame.grid(row=current_row, column=0, sticky='ew', padx=2, pady=1)

        inner_trade_type_buttons_frame = ctk.CTkFrame(trade_type_value_frame, fg_color="transparent")
        inner_trade_type_buttons_frame.pack(side="right", anchor="e")

        selected_trade_type = all_filters_data['trade_type']
        # No 'و...' needed as it's a single selection
        display_trade_type_text = ""
        if selected_trade_type == "همه": display_trade_type_text = process_persian_text_for_matplotlib("همه انواع")
        elif selected_trade_type == "Profit": display_trade_type_text = process_persian_text_for_matplotlib("سودده")
        elif selected_trade_type == "Loss": display_trade_type_text = process_persian_text_for_matplotlib("زیان‌ده")
        elif selected_trade_type == "RF": display_trade_type_text = process_persian_text_for_matplotlib("ریسک فری")

        ctk.CTkButton(inner_trade_type_buttons_frame,
                        text=display_trade_type_text,
                        font=("Vazirmatn", 11, "bold"),
                        fg_color=button_category_colors["trade_type"],
                        text_color=button_text_color,
                        hover_color=button_category_colors["trade_type"],
                        corner_radius=15, width=80, height=25).pack(side="right", padx=2)
        current_row += 1

        # --- Errors ---
        error_label = ctk.CTkLabel(self.summary_table_frame, text=process_persian_text_for_matplotlib('اشتباهات:'),
                                   font=("Vazirmatn", 12), text_color="#424242", anchor='e')
        error_label.grid(row=current_row, column=1, sticky='e', padx=2, pady=1)

        error_value_frame = ctk.CTkFrame(self.summary_table_frame, fg_color="transparent")
        error_value_frame.grid(row=current_row, column=0, sticky='ew', padx=2, pady=1)

        inner_error_buttons_frame = ctk.CTkFrame(error_value_frame, fg_color="transparent")
        inner_error_buttons_frame.pack(side="right", anchor="e")

        selected_errors = all_filters_data['errors']
        if selected_errors == "همه خطاها":
            ctk.CTkButton(inner_error_buttons_frame,
                            text=process_persian_text_for_matplotlib('همه خطاها'),
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=button_category_colors["errors"],
                            text_color=button_text_color,
                            hover_color=button_category_colors["errors"],
                            corner_radius=15, width=90, height=25).pack(side="right", padx=2)
        elif isinstance(selected_errors, list) and selected_errors:
            displayed_count = 0
            for error_text in selected_errors:
                if displayed_count < summary_display_limit:
                    ctk.CTkButton(inner_error_buttons_frame,
                                    text=process_persian_text_for_matplotlib(error_text),
                                    font=("Vazirmatn", 11, "bold"),
                                    fg_color=button_category_colors["errors"],
                                    text_color=button_text_color,
                                    hover_color=button_category_colors["errors"],
                                    corner_radius=15, width=80, height=25).pack(side="right", padx=2)
                    displayed_count += 1
                else:
                    ctk.CTkLabel(inner_error_buttons_frame,
                                 text=process_persian_text_for_matplotlib(f"و... ({len(selected_errors) - displayed_count} مورد دیگر)"),
                                 font=("Vazirmatn", 11), text_color=button_text_color).pack(side="right", padx=2)
                    break
        else:
            ctk.CTkButton(inner_error_buttons_frame,
                            text=process_persian_text_for_matplotlib('هیچکدام'),
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=button_category_colors["errors"],
                            text_color=button_text_color,
                            hover_color=button_category_colors["errors"],
                            corner_radius=15, width=80, height=25).pack(side="right", padx=2)
        current_row += 1

        # --- Hourly Filter ---
        hourly_label = ctk.CTkLabel(self.summary_table_frame, text=process_persian_text_for_matplotlib('ساعات روز:'),
                                    font=("Vazirmatn", 12), text_color="#424242", anchor='e')
        hourly_label.grid(row=current_row, column=1, sticky='e', padx=2, pady=1)

        hourly_value_frame = ctk.CTkFrame(self.summary_table_frame, fg_color="transparent")
        hourly_value_frame.grid(row=current_row, column=0, sticky='ew', padx=2, pady=1)

        inner_hourly_buttons_frame = ctk.CTkFrame(hourly_value_frame, fg_color="transparent")
        inner_hourly_buttons_frame.pack(side="right", anchor="e")

        hourly_selection = all_filters_data['hourly']
        hourly_summary_elements = []

        if hourly_selection["mode"] == "full_session":
            hourly_summary_elements.append(process_persian_text_for_matplotlib("سشن کامل"))
            # Optionally add session names if not "همه"
            if isinstance(all_filters_data['sessions'], list) and all_filters_data['sessions']:
                user_tz = db_manager.get_default_timezone()
                all_session_details = db_manager.get_session_times_with_display_utc(user_tz)
                display_sessions_texts = []
                session_filter_instance = self.filter_frames["sessions"]
                for key in all_filters_data['sessions']:
                    details = all_session_details.get(key)
                    if details:
                        session_display_name = session_filter_instance.session_names_map.get(key, key.capitalize())
                        display_sessions_texts.append(f"{session_display_name} ({details['start_display']} - {details['end_display']})")
                if display_sessions_texts:
                    hourly_summary_elements.append(process_persian_text_for_matplotlib(", ".join(display_sessions_texts)))
            elif all_filters_data['sessions'] == "همه":
                hourly_summary_elements.append(process_persian_text_for_matplotlib("همه سشن‌ها"))

            ctk.CTkButton(inner_hourly_buttons_frame,
                            text=process_persian_text_for_matplotlib(" ".join(hourly_summary_elements)),
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=button_category_colors["hourly"],
                            text_color=button_text_color,
                            hover_color=button_category_colors["hourly"],
                            corner_radius=15, width=150, height=25).pack(side="right", padx=2)

        elif hourly_selection["mode"] == "session_segmentation":
            segments_data = hourly_selection.get("segments")
            segment_count = hourly_selection.get("segment_count")

            hourly_summary_elements.append(process_persian_text_for_matplotlib("تفکیک سشن"))
            if segment_count:
                hourly_summary_elements.append(process_persian_text_for_matplotlib(f"({segment_count} قسمت)"))

            if segments_data and isinstance(segments_data, list):
                session_segments_map = {}
                session_filter_instance = self.filter_frames["sessions"]
                user_tz = db_manager.get_default_timezone()
                all_session_details = db_manager.get_session_times_with_display_utc(user_tz)

                for seg in segments_data:
                    s_key = seg.get("session_key")
                    if s_key not in session_segments_map:
                        session_segments_map[s_key] = []
                    session_segments_map[s_key].append(f"{seg['start']}-{seg['end']}")

                displayed_count = 0
                for s_key, times in session_segments_map.items():
                    session_name = session_filter_instance.session_names_map.get(s_key, s_key.capitalize())
                    # Display each segment part as a button if needed, or combine them
                    for t_str in times:
                        if displayed_count < summary_display_limit:
                            ctk.CTkButton(inner_hourly_buttons_frame,
                                            text=process_persian_text_for_matplotlib(f"{session_name}: {t_str}"),
                                            font=("Vazirmatn", 11, "bold"),
                                            fg_color=button_category_colors["hourly"],
                                            text_color=button_text_color,
                                            hover_color=button_category_colors["hourly"],
                                            corner_radius=15, width=150, height=25).pack(side="right", padx=2)
                            displayed_count += 1
                        else:
                            ctk.CTkLabel(inner_hourly_buttons_frame,
                                         text=process_persian_text_for_matplotlib(f"و... ({len(segments_data) - displayed_count} مورد دیگر)"),
                                         font=("Vazirmatn", 11), text_color=button_text_color).pack(side="right", padx=2)
                            break
                    if displayed_count >= summary_display_limit:
                        break
            else:
                ctk.CTkButton(inner_hourly_buttons_frame,
                                text=process_persian_text_for_matplotlib(f"تفکیک سشن ({segment_count} قسمت) - بازه‌ای انتخاب نشده است."),
                                font=("Vazirmatn", 11, "bold"),
                                fg_color=button_category_colors["hourly"],
                                text_color=button_text_color,
                                hover_color=button_category_colors["hourly"],
                                corner_radius=15, width=250, height=25).pack(side="right", padx=2)

        elif hourly_selection["mode"] == "custom_hour_minute":
            selected_intervals = hourly_selection.get("custom_intervals", [])
            granularity_value = hourly_selection.get("granularity")

            granularity_display_name_map = {
                60: process_persian_text_for_matplotlib("ساعتی کامل"),
                30: process_persian_text_for_matplotlib("نیم‌ساعتی"),
                15: process_persian_text_for_matplotlib("۱۵ دقیقه‌ای")
            }
            granularity_text = granularity_display_name_map.get(granularity_value, process_persian_text_for_matplotlib("ناشناس"))
            
            # Combine granularity with initial text
            ctk.CTkButton(inner_hourly_buttons_frame,
                            text=process_persian_text_for_matplotlib(f"تفکیک ساعت و دقیقه ({granularity_text})"),
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=button_category_colors["hourly"],
                            text_color=button_text_color,
                            hover_color=button_category_colors["hourly"],
                            corner_radius=15, width=200, height=25).pack(side="right", padx=2)

            displayed_count = 0
            for i, interval in enumerate(selected_intervals):
                if displayed_count < summary_display_limit:
                    ctk.CTkButton(inner_hourly_buttons_frame,
                                    text=process_persian_text_for_matplotlib(f"{interval['start']}-{interval['end']}"),
                                    font=("Vazirmatn", 11, "bold"),
                                    fg_color=button_category_colors["hourly"],
                                    text_color=button_text_color,
                                    hover_color=button_category_colors["hourly"],
                                    corner_radius=15, width=100, height=25).pack(side="right", padx=2)
                    displayed_count += 1
                else:
                    ctk.CTkLabel(inner_hourly_buttons_frame,
                                 text=process_persian_text_for_matplotlib(f"و... ({len(selected_intervals) - displayed_count} مورد دیگر)"),
                                 font=("Vazirmatn", 11), text_color=button_text_color).pack(side="right", padx=2)
                    break
            
            if not selected_intervals:
                 ctk.CTkButton(inner_hourly_buttons_frame,
                                text=process_persian_text_for_matplotlib("هیچ بازه‌ای انتخاب نشده است."),
                                font=("Vazirmatn", 11, "bold"),
                                fg_color=button_category_colors["hourly"],
                                text_color=button_text_color,
                                hover_color=button_category_colors["hourly"],
                                corner_radius=15, width=180, height=25).pack(side="right", padx=2)
        
        current_row += 1
        
        # Ensure the layout is updated after adding buttons
        self.summary_table_frame.update_idletasks()


    def _generate_report(self):
        """
        این متد فیلترهای فعلی را جمع‌آوری کرده و یک گزارش را تولید (یا نمایش می‌دهد).
        این متد برای دکمه 'تهیه گزارش' (فیلترهای فعلی) استفاده می‌شود.
        """
        filters = self._get_current_filters_selection()
        self._validate_and_process_report(filters)

    def _generate_report_from_template(self):
        """
        گزارشی را بر اساس قالب انتخاب شده از Treeview تولید می‌کند.
        این متد، فیلترهای قالب را بارگذاری کرده و سپس _validate_and_process_report را فراخوانی می‌کند.
        """
        selected_item = self.templates_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", process_persian_text_for_matplotlib("لطفاً یک قالب گزارش را انتخاب کنید."))
            return

        template_id = int(self.templates_tree.item(selected_item[0], 'values')[0])
        template_data = db_manager.get_report_template_by_id(template_id)
        if template_data and 'filters_json' in template_data:
            filters_to_load = template_data['filters_json']
            self._validate_and_process_report(filters_to_load)
        else:
            messagebox.showerror("Error", process_persian_text_for_matplotlib("خطا در بارگذاری قالب گزارش برای تهیه گزارش."))

    def _validate_and_process_report(self, filters):
        """
        فیلترها را اعتبارسنجی کرده و عملیات نهایی تولید گزارش را انجام می‌دهد.
        (این تابع جایگزین مستقیم فراخوانی detail_frame.update_report می‌شود)
        """
        date_range_selection = filters.get("date_range", {})
        if date_range_selection:
            try:
                start_date_obj = datetime.strptime(date_range_selection["start_date"], '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(date_range_selection["end_date"], '%Y-%m-%d').date()
                if start_date_obj > end_date_obj:
                    messagebox.showwarning("Date Error", process_persian_text_for_matplotlib("تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد."))
                    return
            except ValueError:
                messagebox.showerror("Date Error", process_persian_text_for_matplotlib("فرمت تاریخ نامعتبر است. لطفاً از فرمت YYYY-MM-DD استفاده کنید."))
                return

        instrument_selection = filters.get("instruments")
        if isinstance(instrument_selection, list) and not instrument_selection:
             messagebox.showwarning("Symbol Selection", process_persian_text_for_matplotlib("لطفاً حداقل یک نماد را انتخاب کنید."))
             return
        
        # نمایش فیلترها (به عنوان یک placeholder)
        report_summary_text = f"گزارش برای فیلترهای زیر آماده است:\n\n"
        for key, value in filters.items():
            report_summary_text += f"{key}: {value}\n"

        # Update the filler_label to show report content summary
        # این قسمت دیگر وجود ندارد: self.filler_label.configure(text=process_persian_text_for_matplotlib(report_summary_text))
        messagebox.showinfo("Report Generated", process_persian_text_for_matplotlib("گزارش با فیلترهای انتخابی تولید شد. (جزئیات در کنسول)."))
        print("Generated Report with filters:", filters)

    def _get_current_filters_selection(self):
        """
        تمام فیلترهای انتخاب شده از هر فریم فیلتر را جمع‌آوری و به صورت دیکشنری برمی‌گرداند.
        """
        filters = {}
        filters["date_range"] = self.filter_frames["date_range"].get_selection()
        filters["instruments"] = self.filter_frames["instruments"].get_selection()
        filters["sessions"] = self.filter_frames["sessions"].get_selection()
        filters["trade_type"] = self.filter_frames["trade_type"].get_selection()
        filters["errors"] = self.filter_frames["errors"].get_selection()
        filters["hourly"] = self.filter_frames["hourly"].get_selection()
        filters["weekday"] = self.filter_frames["weekday"].get_selection()
        return filters

    def _save_report_template(self):
        """
        فیلترهای فعلی را به عنوان یک قالب جدید ذخیره می‌کند یا قالب موجود را به‌روزرسانی می‌کند.
        """
        current_filters = self._get_current_filters_selection()

        if self.is_editing_template and self.editing_template_id:
            # Update existing template
            template_name = self.templates_tree.item(str(self.editing_template_id), 'values')[1]
            confirm = messagebox.askyesno("Confirm Update",
                                          process_persian_text_for_matplotlib(f"آیا مطمئن هستید که می‌خواهید قالب '{template_name}' را با فیلترهای فعلی به‌روزرسانی کنید؟"),
                                          parent=self)
            if not confirm:
                return

            if db_manager.update_report_template(self.editing_template_id, template_name, current_filters):
                messagebox.showinfo("Success", process_persian_text_for_matplotlib(f"قالب '{template_name}' با موفقیت به‌روزرسانی شد."))
                self._populate_templates_list()
                self._reset_edit_mode_ui()
            else:
                messagebox.showerror("Error", process_persian_text_for_matplotlib("خطا در به‌روزرسانی قالب."))
        else:
            # Save as new template
            template_name = simpledialog.askstring("Template Name",
                                                   process_persian_text_for_matplotlib("لطفاً نامی برای این قالب گزارش وارد کنید:"),
                                                   parent=self)
            if not template_name:
                messagebox.showwarning("Cancelled", process_persian_text_for_matplotlib("ذخیره‌سازی قالب لغو شد."))
                return

            template_name = template_name.strip()
            if not template_name:
                messagebox.showerror("Error", process_persian_text_for_matplotlib("نام قالب نمی‌تواند خالی باشد."))
                return

            if db_manager.save_report_template(template_name, current_filters):
                messagebox.showinfo("Success", process_persian_text_for_matplotlib(f"قالب '{template_name}' با موفقیت ذخیره شد."))
                self._populate_templates_list()
            else:
                messagebox.showerror("Error", process_persian_text_for_matplotlib(f"خطا در ذخیره قالب. نام '{template_name}' ممکن است قبلاً وجود داشته باشد."))

    def _populate_templates_list(self):
        """
        لیست همه قالب‌های گزارش ذخیره شده (ID و نام) را از دیتابیس خوانده و Treeview را پر می‌کند.
        """
        for item in self.templates_tree.get_children():
            self.templates_tree.delete(item)

        templates = db_manager.get_report_templates()
        for template in templates:
            self.templates_tree.insert("", "end", iid=str(template['id']),
                                       values=(template['id'], process_persian_text_for_matplotlib(template['name'])),
                                       tags=('TemplateName',)
                                       )
        self._clear_template_selection() # Deselects everything and disables buttons

    def _on_template_selected(self, event):
        """
        وقتی آیتمی در Treeview انتخاب می‌شود، دکمه‌های عملیاتی را فعال می‌کند.
        """
        selected_item = self.templates_tree.selection()
        if selected_item:
            self.edit_template_button.configure(state="normal") # "ویرایش قالب"
            self.generate_report_button.configure(state="normal") # "تهیه گزارش"
            self.edit_template_name_button.configure(state="normal")
            self.delete_template_button.configure(state="normal")
            self.copy_template_button.configure(state="normal")
        else:
            self._clear_template_selection()

    def _clear_template_selection(self):
        """
        انتخاب فعلی Treeview را پاک کرده و دکمه‌های عملیاتی را غیرفعال می‌کند.
        """
        if hasattr(self, 'templates_tree'):
            self.templates_tree.selection_remove(self.templates_tree.selection())

        if hasattr(self, 'edit_template_button'):
            self.edit_template_button.configure(state="disabled")
            self.generate_report_button.configure(state="disabled")
            self.edit_template_name_button.configure(state="disabled")
            self.delete_template_button.configure(state="disabled")
            self.copy_template_button.configure(state="disabled")
        
        if self.is_editing_template:
            # If in edit mode, keep Save/Cancel enabled, but don't automatically reset filters
            pass
        else:
            # In normal mode, ensure Save is enabled for new templates, Cancel is for reset
            self.save_template_button.configure(text=process_persian_text_for_matplotlib("ذخیره قالب گزارش"), fg_color="#007BFF", hover_color="#0056B3")
            self.reset_cancel_button.configure(text=process_persian_text_for_matplotlib("ریست فیلترها"), fg_color="#6C757D", hover_color="#5A6268")
            self.is_editing_template = False
            self.editing_template_id = None
            self.original_filters_before_edit = {}


    def _reset_edit_mode_ui(self):
        """Resets the UI elements related to template editing mode."""
        self.is_editing_template = False
        self.editing_template_id = None
        self.original_filters_before_edit = {}
        
        self.save_template_button.configure(text=process_persian_text_for_matplotlib("ذخیره قالب گزارش"), fg_color="#007BFF", hover_color="#0056B3")
        self.reset_cancel_button.configure(text=process_persian_text_for_matplotlib("ریست فیلترها"), fg_color="#6C757D", hover_color="#5A6268")
        self.templates_tree.selection_remove(self.templates_tree.selection())
        self._on_template_selected(None) # Call to disable other template buttons


    def _edit_selected_template(self):
        """
        فیلترهای یک قالب خاص را بارگذاری می‌کند و حالت برنامه را به "ویرایش قالب" تغییر می‌دهد.
        """
        selected_item = self.templates_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", process_persian_text_for_matplotlib("لطفاً یک قالب گزارش را برای ویرایش انتخاب کنید."))
            return

        template_id = int(self.templates_tree.item(selected_item[0], 'values')[0])
        template_data = db_manager.get_report_template_by_id(template_id)
        if template_data and 'filters_json' in template_data:
            self.original_filters_before_edit = self._get_current_filters_selection() # Save current filters
            self.is_editing_template = True
            self.editing_template_id = template_id

            filters_to_load = template_data['filters_json']
            self._apply_filters_to_ui(filters_to_load)

            # Change button texts for edit mode
            self.save_template_button.configure(text=process_persian_text_for_matplotlib(f"ذخیره تغییرات قالب '{template_data['name']}'"),
                                                fg_color="#28A745", hover_color="#218838")
            self.reset_cancel_button.configure(text=process_persian_text_for_matplotlib("لغو ویرایش"),
                                               fg_color="#DC3545", hover_color="#C82333")

            messagebox.showinfo("Edit Mode", process_persian_text_for_matplotlib(f"Template '{template_data['name']}' Loaded; edit and save!"))
            # Clear selection in treeview to prevent accidental re-loading
            self.templates_tree.selection_remove(self.templates_tree.selection())
            self._on_template_selected(None) # Disable other template buttons
        else:
            messagebox.showerror("Error", process_persian_text_for_matplotlib("خطا در بارگذاری قالب گزارش برای ویرایش."))

    def _apply_filters_to_ui(self, filters_data):
        """
        Applies filter data to the UI elements of each filter frame.
        This is a helper function used by _edit_selected_template and _reset_filters.
        """
        self.filter_frames["date_range"].set_selection(
            filters_data.get("date_range", {}).get("start_date", (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')),
            filters_data.get("date_range", {}).get("end_date", datetime.now().strftime('%Y-%m-%d')),
            filters_data.get("date_range", {}).get("preset", "custom")
        )
        self.filter_frames["instruments"].set_selection(filters_data.get("instruments", [])) # Changed default to empty list
        self.filter_frames["sessions"].set_selection(filters_data.get("sessions", "همه"))
        self.filter_frames["trade_type"].set_selection(filters_data.get("trade_type", "همه"))
        self.filter_frames["errors"].set_selection(filters_data.get("errors", "همه خطاها"))

        hourly_filter_data = filters_data.get("hourly", {})
        self.filter_frames["hourly"].set_selection(
            mode=hourly_filter_data.get("mode", "full_session"),
            segments=hourly_filter_data.get("segments"),
            custom_intervals=hourly_filter_data.get("custom_intervals"),
            granularity=hourly_filter_data.get("granularity")
        )
        self.filter_frames["weekday"].set_selection(filters_data.get("weekday", "همه"))
        self._on_filter_changed() # Trigger update for summary and dependent filters


    def _reset_filters(self, initial_load=False):
        """
        Resets all filters to their default state or cancels template editing.
        """
        if self.is_editing_template and not initial_load:
            # Cancel edit mode: revert to original filters
            confirm_cancel = messagebox.askyesno("Cancel Edit",
                                                 "Sure to cancel edit? No edit(s) will saved!",
                                                 parent=self)
            if confirm_cancel:
                self._apply_filters_to_ui(self.original_filters_before_edit) # Revert to saved filters
                self._reset_edit_mode_ui() # Reset UI for edit mode
                messagebox.showinfo("Edit Cancelled", "Template Edit canceled.")
            return
        
        # Reset all filters to default
        # Date Range: Set to "last_30_days" as default
        self.filter_frames["date_range"].current_selection_var.set("last_30_days")
        self.filter_frames["date_range"]._set_last_n_days(30)() # Explicitly call the command to set dates

        # Other filters: Set to "None selected" or clear selection
        # Note: set_selection in these filters also triggers internal updates if needed.
        self.filter_frames["instruments"].set_selection([]) # <<< اینجا باید مطمئن بشی که لیست خالی پاس داده میشه
        self.filter_frames["sessions"].set_selection("همه")
        self.filter_frames["trade_type"].set_selection("همه")
        self.filter_frames["errors"].set_selection("همه خطاها")
        self.filter_frames["hourly"].set_selection(mode="full_session", segments=None, custom_intervals=None, granularity=None)
        self.filter_frames["weekday"].set_selection("همه")
        
        # Ensure internal state of hourly filter is reloaded based on default sessions.
        # This will be handled by _on_filter_changed which is called next.

        self._on_filter_changed() # Force update after resetting all

        # Only show confirmation message if not initial load
        if not initial_load:
            messagebox.showinfo("Filters Reset", "All filters have been reset to default.")
        
        # Ensure edit mode UI is reset if we were in edit mode and chose to reset
        self._reset_edit_mode_ui()
        
    def _copy_template(self):
        """
        Creates a duplicate of the selected template with a modified name.
        """
        selected_item = self.templates_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", process_persian_text_for_matplotlib("لطفاً یک قالب گزارش را برای کپی کردن انتخاب کنید."))
            return

        template_id = int(self.templates_tree.item(selected_item[0], 'values')[0])
        original_name = self.templates_tree.item(selected_item[0], 'values')[1]
        
        template_data = db_manager.get_report_template_by_id(template_id)
        if not template_data:
            messagebox.showerror("Error", process_persian_text_for_matplotlib("خطا در یافتن قالب اصلی برای کپی کردن."))
            return

        new_name_base = original_name
        # اطمینان حاصل کن که " (کپی)" به درستی تشخیص داده و حذف شود
        persian_copy_suffix = process_persian_text_for_matplotlib(" (کپی)")
        if new_name_base.endswith(persian_copy_suffix):
            new_name_base = new_name_base[:-len(persian_copy_suffix)].strip()

        # ابتدا نام جدید را با " (کپی)" فارسی بساز
        new_name = new_name_base + persian_copy_suffix
        
        counter = 1
        # تا زمانی که نام تکراری نباشد، به آن " (کپی X)" اضافه کن
        while not db_manager.save_report_template(new_name, template_data['filters_json']):
            # مطمئن شو که " (کپی X)" هم به درستی فارسی پردازش شود
            new_name = new_name_base + process_persian_text_for_matplotlib(f" (کپی {counter})")
            counter += 1
            if counter > 100: # جلوگیری از حلقه بی‌نهایت
                messagebox.showerror("Error", process_persian_text_for_matplotlib("تعداد کپی‌های تکراری بیش از حد است، لطفاً نام جدید را به صورت دستی وارد کنید."))
                return

        messagebox.showinfo("Success", f"Template '{original_name}' duplicated as '{new_name}'")
        self._populate_templates_list()

    def _edit_template_name(self):
        """
        نام قالب انتخاب شده را ویرایش می‌کند.
        """
        selected_item = self.templates_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "No template selected to edit name.")
            return

        template_id = int(self.templates_tree.item(selected_item[0], 'values')[0])
        current_name = self.templates_tree.item(selected_item[0], 'values')[1]

        new_name = simpledialog.askstring("Edit Template Name",
                                          process_persian_text_for_matplotlib(f"Enter new name for «{current_name}» :"),
                                          initialvalue=current_name,
                                          parent=self)

        if not new_name:
            messagebox.showwarning("Cancelled", process_persian_text_for_matplotlib("ویرایش نام قالب لغو شد."))
            return

        new_name = new_name.strip()
        if not new_name:
            messagebox.showerror("Error", process_persian_text_for_matplotlib("نام قالب نمی‌تواند خالی باشد."))
            return

        if new_name == current_name:
            messagebox.showinfo("No Change", process_persian_text_for_matplotlib("نام جدید با نام فعلی یکسان است."))
            return

        template_data = db_manager.get_report_template_by_id(template_id)
        if template_data and db_manager.update_report_template(template_id, new_name, template_data['filters_json']):
            messagebox.showinfo("Success", process_persian_text_for_matplotlib(f"نام قالب به '{new_name}' تغییر یافت."))
            self._populate_templates_list()
        else:
            messagebox.showerror("Error", process_persian_text_for_matplotlib("خطا در ویرایش نام قالب. ممکن است نام قبلاً وجود داشته باشد."))

    def _delete_template(self):
        """
        قالب انتخاب شده را حذف می‌کند.
        """
        selected_item = self.templates_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", process_persian_text_for_matplotlib("هیچ قالب گزارشی برای حذف انتخاب نشده است."))
            return

        template_id = int(self.templates_tree.item(selected_item[0], 'values')[0])
        template_name = self.templates_tree.item(selected_item[0], 'values')[1]

        confirm = messagebox.askyesno("Confirm Deletion",
                                      process_persian_text_for_matplotlib(f"آیا مطمئن هستید که می‌خواهید قالب '{template_name}' را حذف کنید؟"),
                                      parent=self)

        if confirm:
            if db_manager.delete_report_template(template_id):
                messagebox.showinfo("Success", process_persian_text_for_matplotlib(f"قالب '{template_name}' با موفقیت حذف شد."))
                self._populate_templates_list()
            else:
                messagebox.showerror("Error", process_persian_text_for_matplotlib("خطا در حذف قالب گزارش."))


# برای تست مستقل (فقط برای توسعه)
if __name__ == "__main__":
    class MockDBManager:
        _mock_templates = {}
        _next_template_id = 1

        def get_unique_symbols(self, start_date=None, end_date=None):
            if start_date and end_date:
                print(f"Mock DB: Getting symbols for {start_date} to {end_date}")
                if start_date >= "2024-07-01":
                    return ["USDCAD", "EURCAD"]
                else:
                    return ["US30", "XAUUSD", "EURUSD", "GBPUSD", "NZDUSD", "AUDCAD"]
            return ["US30", "XAUUSD", "EURUSD", "GBPUSD", "NZDUSD", "AUDCAD"]
        def get_first_trade_date(self):
            return "2023-01-01"
        def get_working_days(self):
            return [0, 1, 2, 3, 4]
        def get_session_times_utc(self):
            return {
                'ny': {'start': '13:30', 'end': '20:00'},
                'london': {'start': '07:00', 'end': '15:30'},
                'sydney': {'start': '00:00', 'end': '06:00'},
                'tokyo': {'start': '00:00', 'end': '06:00'}
            }
        def get_session_times_with_display_utc(self, user_timezone_name):
            mock_sessions = {
                'ny': {'start_utc': '13:30', 'end_utc': '20:00', 'start_display': '17:00', 'end_display': '23:30'},
                'sydney': {'start_utc': '00:00', 'end_utc': '06:00', 'start_display': '03:30', 'end_display': '09:30'},
                'tokyo': {'start_utc': '00:00', 'end_utc': '06:00', 'start_display': '03:30', 'end_display': '09:30'},
                'london': {'start_utc': '07:00', 'end_utc': '15:30', 'start_display': '10:30', 'end_display': '19:00'}
            }
            return mock_sessions
        def get_trades_by_filters(self, filters):
            print(f"Mock DB: Fetching trades with filters: {filters}")
            return []
        def get_unique_errors_by_filters(self, start_date=None, end_date=None, trade_type_filter=None):
            print(f"Mock DB: Getting errors for date range {start_date}-{end_date} and trade type {trade_type_filter}")
            if start_date and start_date < "2024-01-01":
                return ["اشتباه حجم زیاد", "ورود زودهنگام", "نداشتن حد ضرر"]
            return ["اشتباه حجم زیاد", "ورود زودهنگام"]
        def get_default_timezone(self):
            return "Asia/Tehran"

        # --- Mock methods for report templates ---
        def save_report_template(self, name, filters_data):
            for tid, tdata in self._mock_templates.items():
                if tdata['name'] == name:
                    print(f"Mock DB: Template '{name}' already exists.")
                    return False
            self._mock_templates[self._next_template_id] = {'id': self._next_template_id, 'name': name, 'filters_json': json.dumps(filters_data)}
            print(f"Mock DB: Saved template '{name}' with ID {self._next_template_id}")
            self._next_template_id += 1
            return True

        def get_report_templates(self):
            return [{'id': tid, 'name': t['name']} for tid, t in self._mock_templates.items()]

        def get_report_template_by_id(self, template_id):
            template = self._mock_templates.get(template_id)
            if template:
                return {'id': template['id'], 'name': template['name'], 'filters_json': json.loads(template['filters_json'])}
            return None

        def update_report_template(self, template_id, new_name, new_filters_data):
            if template_id not in self._mock_templates:
                return False
            for tid, tdata in self._mock_templates.items():
                if tdata['name'] == new_name and tid != template_id:
                    print(f"Mock DB: Template '{new_name}' already exists for another ID.")
                    return False

            if new_filters_data:
                self._mock_templates[template_id]['filters_json'] = json.dumps(new_filters_data)
            self._mock_templates[template_id]['name'] = new_name
            print(f"Mock DB: Updated template ID {template_id} to name '{new_name}'")
            return True

        def delete_report_template(self, template_id):
            if template_id in self._mock_templates:
                del self._mock_templates[template_id]
                print(f"Mock DB: Deleted template ID {template_id}")
                return True
            return False

    import db_manager as original_db_manager
    original_db_manager.get_unique_symbols = MockDBManager().get_unique_symbols
    original_db_manager.get_first_trade_date = MockDBManager().get_first_trade_date
    original_db_manager.get_working_days = MockDBManager().get_working_days
    original_db_manager.get_session_times_utc = MockDBManager().get_session_times_utc
    original_db_manager.get_session_times_with_display_utc = MockDBManager().get_session_times_with_display_utc
    original_db_manager.get_trades_by_filters = MockDBManager().get_trades_by_filters
    original_db_manager.get_unique_errors_by_filters = MockDBManager().get_unique_errors_by_filters
    original_db_manager.get_default_timezone = MockDBManager().get_default_timezone

    mock_db_instance = MockDBManager()
    original_db_manager.save_report_template = mock_db_instance.save_report_template
    original_db_manager.get_report_templates = mock_db_instance.get_report_templates
    original_db_manager.get_report_template_by_id = mock_db_instance.get_report_template_by_id
    original_db_manager.update_report_template = mock_db_instance.update_report_template
    original_db_manager.delete_report_template = mock_db_instance.delete_report_template


    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root_test = ctk.CTk()
    root_test.withdraw()

    mock_open_windows = []
    # Replace this with direct instance creation for testing purposes
    # report_selection_window.ReportSelectionWindow(root_test, mock_open_windows)
    app = ReportSelectionWindow(root_test, mock_open_windows)
    root_test.mainloop()