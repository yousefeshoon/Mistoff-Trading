# report_details.py

import customtkinter as ctk
from persian_chart_utils import process_persian_text_for_matplotlib
import tkinter as tk
from tkinter import ttk # For Treeview
from collections import Counter # For counting errors
import db_manager
from datetime import datetime, timedelta

class ReportDetailsFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Transparent background for the main frame
        self.configure(fg_color="transparent")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Row for report type buttons
        self.grid_rowconfigure(1, weight=1) # Row for dynamic report content

        # Frame for Report Type Buttons (e.g., Summary, Hourly, Errors)
        self.report_buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.report_buttons_frame.grid(row=0, column=0, padx=10, pady=(5, 15), sticky="ew")
        self.report_buttons_frame.grid_columnconfigure((0,1,2,3,4), weight=1) # Distribute buttons evenly

        self.report_content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.report_content_area.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.report_content_area.grid_columnconfigure(0, weight=1)
        self.report_content_area.grid_rowconfigure(0, weight=1)

        self.current_report_type_frame = None # To keep track of the currently displayed report content frame
        self.current_filtered_trades = [] # Store filtered trades to use across reports
        self.current_filters = {} # Store current filters
        self.current_template_name = "" # Store current template name


        self._create_report_type_buttons() # Call method to create buttons
        
        # Initial placeholder content setup (now includes error_frequency_report_frame)
        self._setup_report_content_frames()

        # NOTE: Initial content selection is now handled at the end of update_report_content
        # to ensure filtered trades are loaded before _display_error_frequency_report is called.


    def _create_report_type_buttons(self):
        # Define button texts and their corresponding keys for content mapping
        button_specs = [
            ("summary", "خلاصه گزارش", "#28A745"),  # Green
            ("hourly", "گزارش ساعتی", "#FFC107"),    # Amber
            ("errors", "گزارش اشتباهات", "#17A2B8"), # Info Blue
            ("trade_hour_analysis", "آنالیز ساعات ترید", "#DC3545"), # Renamed from "growth", color for "hourly_segmentation" in filter window
            ("error_frequency", "خروجی با فیلتر فعلی", "#6F42C1") # New color for this button, formerly "other"
        ]

        self.report_buttons = {}
        for i, (key, text, color) in enumerate(button_specs):
            button = ctk.CTkButton(self.report_buttons_frame,
                                   text=process_persian_text_for_matplotlib(text),
                                   command=lambda k=key: self._show_report_content(k),
                                   font=("Vazirmatn", 12, "bold"),
                                   fg_color=color,
                                   text_color="white",
                                   hover_color=self._darken_color(color, 20),
                                   corner_radius=15 if key == "error_frequency" else 8, # 15 for "خروجی با فیلتر فعلی", 8 for others
                                   height=40,
                                   width=150)
            button.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
            self.report_buttons[key] = button

    def _setup_report_content_frames(self):
        # Create frames for each report type. These will hold the actual content.
        
        # Summary Report Frame
        self.summary_report_frame = ctk.CTkFrame(self.report_content_area, fg_color="transparent")
        self.summary_report_frame.grid_columnconfigure(0, weight=1)
        self.summary_report_frame.grid_rowconfigure(0, weight=1)
        self.summary_report_label = ctk.CTkLabel(self.summary_report_frame, 
                                                 text=process_persian_text_for_matplotlib("محتوای خلاصه گزارش در اینجا نمایش داده خواهد شد."),
                                                 font=("Vazirmatn", 14), text_color="#202124", wraplength=800, anchor="e", justify="right")
        self.summary_report_label.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.report_buttons["summary"].content_frame = self.summary_report_frame

        # Hourly Report Frame
        self.hourly_report_frame = ctk.CTkFrame(self.report_content_area, fg_color="transparent")
        self.hourly_report_frame.grid_columnconfigure(0, weight=1)
        self.hourly_report_frame.grid_rowconfigure(0, weight=1)
        self.hourly_report_label = ctk.CTkLabel(self.hourly_report_frame, 
                                                text=process_persian_text_for_matplotlib("گزارش ساعتی (بر اساس ساعات انتخابی) در اینجا نمایش داده خواهد شد."),
                                                font=("Vazirmatn", 14), text_color="#202124", wraplength=800, anchor="e", justify="right")
        self.hourly_report_label.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.report_buttons["hourly"].content_frame = self.hourly_report_frame

        # Errors Report Frame
        self.errors_report_frame = ctk.CTkFrame(self.report_content_area, fg_color="transparent")
        self.errors_report_frame.grid_columnconfigure(0, weight=1)
        self.errors_report_frame.grid_rowconfigure(0, weight=1)
        self.errors_report_label = ctk.CTkLabel(self.errors_report_frame, 
                                                text=process_persian_text_for_matplotlib("گزارش اشتباهات رایج (بر اساس فیلتر اشتباهات) در اینجا نمایش داده خواهد شد."),
                                                font=("Vazirmatn", 14), text_color="#202124", wraplength=800, anchor="e", justify="right")
        self.errors_report_label.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.report_buttons["errors"].content_frame = self.errors_report_frame
        
        # Trade Hour Analysis Report Frame (formerly Growth Report)
        self.trade_hour_analysis_frame = ctk.CTkFrame(self.report_content_area, fg_color="transparent")
        self.trade_hour_analysis_frame.grid_columnconfigure(0, weight=1)
        self.trade_hour_analysis_frame.grid_rowconfigure(0, weight=1) # Main area for analysis
        self.report_buttons["trade_hour_analysis"].content_frame = self.trade_hour_analysis_frame

        # Error Frequency Report Frame
        self.error_frequency_report_frame = ctk.CTkFrame(self.report_content_area, fg_color="transparent")
        self.error_frequency_report_frame.grid_columnconfigure(0, weight=1)
        self.error_frequency_report_frame.grid_rowconfigure(0, weight=1)
        self.report_buttons["error_frequency"].content_frame = self.error_frequency_report_frame

    def _show_report_content(self, report_type_key):
        if self.current_report_type_frame:
            self.current_report_type_frame.grid_forget()

        new_content_frame = self.report_buttons[report_type_key].content_frame
        
        if new_content_frame:
            new_content_frame.grid(row=0, column=0, sticky="nsew")
            self.current_report_type_frame = new_content_frame

        # Update button colors for visual feedback
        for key, button in self.report_buttons.items():
            original_color = self._get_original_button_color(key)
            if key == report_type_key:
                # Darken the active button to show it's selected
                button.configure(fg_color=self._darken_color(original_color, 15), text_color="white")
            else:
                # Reset inactive buttons to their original color
                button.configure(fg_color=original_color, text_color="white")

        # Trigger specific report generation
        if report_type_key == "trade_hour_analysis":
            self._display_trade_hour_analysis()
        elif report_type_key == "error_frequency":
            self._display_error_frequency_report()
        # Add other report types here if they need specific display logic triggered by button click


    def _darken_color(self, hex_color, percent):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darker_rgb = tuple(max(0, c - int(c * percent / 100)) for c in rgb)
        return '#%02x%02x%02x' % darker_rgb

    def _lighten_color(self, hex_color, percent):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        lighter_rgb = tuple(min(255, c + int((255 - c) * percent / 100)) for c in rgb)
        return '#%02x%02x%02x' % lighter_rgb

    def _get_original_button_color(self, key):
        color_map = {
            "summary": "#28A745",
            "hourly": "#FFC107",
            "errors": "#17A2B8",
            "trade_hour_analysis": "#DC3545", # Matching color of hourly_filter button from report_selection_window
            "error_frequency": "#6F42C1" # New color for this button
        }
        return color_map.get(key, "#6C757D")

    def update_report_content(self, filtered_trades, filters, template_name):
        """
        این تابع برای به‌روزرسانی محتوای گزارش بر اساس تریدهای فیلتر شده و فیلترهای اعمال شده استفاده می‌شود.
        داده‌های فیلتر شده را ذخیره می‌کند تا برای گزارش‌های مختلف قابل استفاده باشد.
        """
        self.current_filtered_trades = filtered_trades
        self.current_filters = filters
        self.current_template_name = template_name

        num_trades = len(filtered_trades)
        
        # Update Summary Report
        summary_text = process_persian_text_for_matplotlib(f"محتوای خلاصه گزارش در اینجا نمایش داده خواهد شد.\n\nتعداد تریدهای فیلتر شده: {num_trades}\nفیلتر اعمال شده: {template_name}")
        self.summary_report_label.configure(text=summary_text)

        # Update Hourly Report (placeholder)
        hourly_info_text = process_persian_text_for_matplotlib(f"گزارش ساعتی برای {num_trades} ترید فیلتر شده.\n\nجزئیات فیلتر ساعات روز: {filters.get('hourly', 'نامشخص')}")
        self.hourly_report_label.configure(text=hourly_info_text)

        # Update Errors Report (placeholder)
        error_info_text = process_persian_text_for_matplotlib(f"گزارش اشتباهات برای {num_trades} ترید فیلتر شده.\n\nخطاهای فیلتر شده: {filters.get('errors', 'نامشخص')}")
        self.errors_report_label.configure(text=error_info_text)
        
        print(f"ReportDetailsFrame: Updated with {num_trades} trades. Filters: {filters}, Template Name: {template_name}")
        
        # Ensure that the error frequency report is displayed by default after content update
        self._show_report_content("error_frequency")


    def _display_error_frequency_report(self):
        """
        Calculates and displays the frequency of errors in the current filtered trades.
        Uses a custom grid layout within a scrollable frame for better control over progress bars.
        """
        # Clear previous content in the error_frequency_report_frame
        for widget in self.error_frequency_report_frame.winfo_children():
            widget.destroy()
        
        # Main scrollable frame to hold all error rows. This handles the scrollbar.
        scrollable_content_frame = ctk.CTkScrollableFrame(self.error_frequency_report_frame, fg_color="transparent")
        scrollable_content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Define column weights for the content within scrollable_content_frame
        # Order: Count, Progress Bar, Percentage, Error Name
        # Weights and minsizes are chosen for fixed-like column widths
        # Adjusted minsize values for better control and fixed-width feel
        scrollable_content_frame.grid_columnconfigure(0, weight=0, minsize=80)  # Count Column (fixed)
        scrollable_content_frame.grid_columnconfigure(1, weight=1)             # Progress Bar Column (takes remaining space)
        scrollable_content_frame.grid_columnconfigure(2, weight=0, minsize=100) # Percentage Column (fixed)
        scrollable_content_frame.grid_columnconfigure(3, weight=0, minsize=250) # Error Name Column (fixed, right-aligned)


        # Header row for the table
        header_row_idx = 0
        ctk.CTkLabel(scrollable_content_frame, text=process_persian_text_for_matplotlib("تعداد"), font=("Vazirmatn", 11, "bold"), anchor="center").grid(row=header_row_idx, column=0, padx=2, pady=5, sticky="ew")
        ctk.CTkLabel(scrollable_content_frame, text=process_persian_text_for_matplotlib("نمودار"), font=("Vazirmatn", 11, "bold"), anchor="w").grid(row=header_row_idx, column=1, padx=2, pady=5, sticky="ew") # Anchor to west (left)
        ctk.CTkLabel(scrollable_content_frame, text=process_persian_text_for_matplotlib("درصد"), font=("Vazirmatn", 11, "bold"), anchor="center").grid(row=header_row_idx, column=2, padx=2, pady=5, sticky="ew") # Anchor to center
        ctk.CTkLabel(scrollable_content_frame, text=process_persian_text_for_matplotlib("خطا"), font=("Vazirmatn", 11, "bold"), anchor="e").grid(row=header_row_idx, column=3, padx=2, pady=5, sticky="ew") # Anchor to east (right)

        # Calculate error frequencies
        error_counts = Counter()
        total_errors_in_filter = 0 

        for trade in self.current_filtered_trades:
            if trade['errors']:
                errors_in_trade = [err.strip() for err in trade['errors'].split(',') if err.strip()]
                for error in set(errors_in_trade): # Count each unique error once per trade
                    error_counts[error] += 1
                    total_errors_in_filter += 1 # Summing up all individual error mentions for percentage base

        if not error_counts:
            no_errors_label = ctk.CTkLabel(scrollable_content_frame, text=process_persian_text_for_matplotlib("هیچ خطایی در تریدهای فیلتر شده یافت نشد."),
                                            font=("Vazirmatn", 12), text_color="gray50", anchor="center")
            no_errors_label.grid(row=1, column=0, columnspan=4, pady=50, sticky="nsew")
            return

        # Sort errors by frequency (descending)
        sorted_errors = sorted(error_counts.items(), key=lambda item: item[1], reverse=True)

        for i, (error_name, count) in enumerate(sorted_errors):
            percentage = (count / total_errors_in_filter) * 100 if total_errors_in_filter > 0 else 0
            
            # Create a frame for each row to better group widgets
            row_frame = ctk.CTkFrame(scrollable_content_frame, fg_color="transparent", height=35) # Fixed height for row
            row_frame.grid(row=i + header_row_idx + 1, column=0, columnspan=4, sticky="ew", pady=1) # Occupy all columns

            # Configure columns within the row_frame to maintain alignment with main scrollable frame
            row_frame.grid_columnconfigure(0, weight=0, minsize=80)  # Count
            row_frame.grid_columnconfigure(1, weight=1)             # Progress Bar
            row_frame.grid_columnconfigure(2, weight=0, minsize=100) # Percentage
            row_frame.grid_columnconfigure(3, weight=0, minsize=250) # Error Name


            # Column 0: Count
            ctk.CTkLabel(row_frame, text=process_persian_text_for_matplotlib(str(count)), 
                         font=("Vazirmatn", 11, "bold", "underline"), anchor="center").grid(row=0, column=0, padx=2, sticky="ew")

            # Column 1: Progress Bar (Chart)
            progress_bar = ctk.CTkProgressBar(row_frame, 
                                              orientation="horizontal", 
                                              mode="determinate", 
                                              height=15, 
                                              corner_radius=5,
                                              fg_color="#E0E0E0", 
                                              progress_color="#DC3545") # Red color for the progress
            progress_bar.set(percentage / 100) # Set value between 0 and 1
            # Just grid it normally, it will fill left-to-right
            progress_bar.grid(row=0, column=1, padx=2, sticky="ew") # No more side="right"


            # Column 2: Percentage
            ctk.CTkLabel(row_frame, text=process_persian_text_for_matplotlib(f"{percentage:.1f}%"),
                         font=("Vazirmatn", 11, "bold", "underline"), anchor="center").grid(row=0, column=2, padx=2, sticky="ew")

            # Column 3: Error Name
            ctk.CTkLabel(row_frame, text=process_persian_text_for_matplotlib(error_name),
                         font=("Vazirmatn", 11, "bold", "underline"), anchor="e", wraplength=300).grid(row=0, column=3, padx=2, sticky="ew")

    def _display_trade_hour_analysis(self):
        """
        Calculates and displays error frequency based on selected hourly filter mode.
        """
        # Clear previous content in the trade_hour_analysis_frame
        for widget in self.trade_hour_analysis_frame.winfo_children():
            widget.destroy()

        scrollable_content_frame = ctk.CTkScrollableFrame(self.trade_hour_analysis_frame, fg_color="transparent")
        scrollable_content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        scrollable_content_frame.grid_columnconfigure(0, weight=1) # Only one column for content sections

        if not self.current_filtered_trades:
            no_trades_label = ctk.CTkLabel(scrollable_content_frame, text=process_persian_text_for_matplotlib("هیچ تریدی برای آنالیز یافت نشد."),
                                            font=("Vazirmatn", 12), text_color="gray50", anchor="center")
            no_trades_label.grid(row=0, column=0, pady=50, sticky="nsew")
            return

        hourly_filter_data = self.current_filters.get("hourly", {})
        current_mode = hourly_filter_data.get("mode")
        user_display_timezone = db_manager.get_default_timezone()
        all_session_times_display = db_manager.get_session_times_with_display_utc(user_display_timezone)
        
        row_idx = 0

        if current_mode == "full_session":
            # Analysis for "Full Session" mode
            selected_sessions = self.current_filters.get("sessions", []) # Get sessions from main filters
            
            # Map session keys to their display names for output
            session_names_map = {
                'ny': 'Newyork', 'sydney': 'Sydney', 'tokyo': 'Tokyo', 'london': 'London'
            }

            if selected_sessions == "همه":
                sessions_to_analyze_keys = list(all_session_times_display.keys())
            elif isinstance(selected_sessions, list) and selected_sessions:
                sessions_to_analyze_keys = selected_sessions
            else:
                sessions_to_analyze_keys = [] # No specific sessions selected, or an empty list
            
            if not sessions_to_analyze_keys:
                no_sessions_selected_label = ctk.CTkLabel(scrollable_content_frame, 
                                                            text=process_persian_text_for_matplotlib("در حالت 'سشن کامل'، سشنی برای آنالیز انتخاب نشده است. لطفاً در تب 'فیلترها' یک یا چند سشن را انتخاب کنید."),
                                                            font=("Vazirmatn", 12), text_color="gray50", anchor="e", wraplength=500, justify="right")
                no_sessions_selected_label.grid(row=row_idx, column=0, pady=10, sticky="ew")
                row_idx += 1
                return

            analysis_results = {} # {session_key: Counter(), ...}
            for sess_key in sessions_to_analyze_keys:
                analysis_results[sess_key] = Counter()

            for trade in self.current_filtered_trades:
                trade_dt_obj = datetime.strptime(f"{trade['date']} {trade['time']}", '%Y-%m-%d %H:%M')
                
                # Check which session(s) the trade falls into
                for sess_key in sessions_to_analyze_keys:
                    session_detail = all_session_times_display.get(sess_key)
                    if session_detail and db_manager._is_trade_in_time_interval(trade_dt_obj, session_detail['start_display'], session_detail['end_display']):
                        if trade['errors']:
                            errors_in_trade = [err.strip() for err in trade['errors'].split(',') if err.strip()]
                            for error in set(errors_in_trade): # Count unique errors per trade for each session
                                analysis_results[sess_key][error] += 1
                        break # Assume a trade only belongs to one primary session for this analysis view


            ctk.CTkLabel(scrollable_content_frame, text=process_persian_text_for_matplotlib("آنالیز خطاها بر اساس سشن‌های کامل"),
                         font=("Vazirmatn", 13, "bold"), text_color="#202124", anchor="e").grid(row=row_idx, column=0, pady=(10, 5), sticky="ew")
            row_idx += 1

            for sess_key, error_counts in analysis_results.items():
                session_display_name = session_names_map.get(sess_key, sess_key.capitalize())
                session_detail_times = all_session_times_display.get(sess_key, {'start_display': 'N/A', 'end_display': 'N/A'})

                session_header_text = process_persian_text_for_matplotlib(f"سشن {session_display_name} ({session_detail_times['start_display']}-{session_detail_times['end_display']})")
                
                # Create a frame for the section (header button + table content)
                section_content_frame = ctk.CTkFrame(scrollable_content_frame, fg_color="transparent")
                section_content_frame.grid(row=row_idx, column=0, pady=(5, 10), sticky="ew")
                section_content_frame.grid_columnconfigure(0, weight=1) # For the table part

                # Header button-like frame to support justify and wraplength for text
                header_button_like_frame = ctk.CTkFrame(section_content_frame,
                                                         fg_color="#4CAF50", corner_radius=8, height=30)
                header_button_like_frame.pack(fill="x", pady=(0, 5))
                header_button_like_frame.pack_propagate(False) # Prevent frame from shrinking below height
                
                ctk.CTkLabel(header_button_like_frame, text=session_header_text,
                             font=("Vazirmatn", 12, "bold"), text_color="white",
                             anchor="e", justify="right", wraplength=300).pack(expand=True, fill="both", padx=5, pady=0) # Adjust padding


                # Now, create the table content for this section within section_content_frame
                table_frame = ctk.CTkFrame(section_content_frame, fg_color="white", corner_radius=8)
                table_frame.pack(fill="both", expand=True, padx=10, pady=(0,5)) # Adjust padx to align with header button's padx
                table_frame.grid_columnconfigure(0, weight=0, minsize=80)  # Count Column
                table_frame.grid_columnconfigure(1, weight=1)             # Progress Bar Column
                table_frame.grid_columnconfigure(2, weight=0, minsize=100) # Percentage Column
                table_frame.grid_columnconfigure(3, weight=0, minsize=250) # Error Name Column

                # Table headers (inside table_frame)
                table_row_offset = 0
                ctk.CTkLabel(table_frame, text=process_persian_text_for_matplotlib("تعداد"), font=("Vazirmatn", 11, "bold"), anchor="center").grid(row=table_row_offset, column=0, padx=2, pady=5, sticky="ew")
                ctk.CTkLabel(table_frame, text=process_persian_text_for_matplotlib("نمودار"), font=("Vazirmatn", 11, "bold"), anchor="w").grid(row=table_row_offset, column=1, padx=2, pady=5, sticky="ew")
                ctk.CTkLabel(table_frame, text=process_persian_text_for_matplotlib("درصد"), font=("Vazirmatn", 11, "bold"), anchor="center").grid(row=table_row_offset, column=2, padx=2, pady=5, sticky="ew")
                ctk.CTkLabel(table_frame, text=process_persian_text_for_matplotlib("خطا"), font=("Vazirmatn", 11, "bold"), anchor="e").grid(row=table_row_offset, column=3, padx=2, pady=5, sticky="ew")
                table_row_offset += 1


                if not error_counts:
                    ctk.CTkLabel(table_frame, text=process_persian_text_for_matplotlib("هیچ خطایی در این سشن یافت نشد."),
                                 font=("Vazirmatn", 11), text_color="gray60", anchor="e").grid(row=table_row_offset, column=0, columnspan=4, padx=20, pady=2, sticky="ew")
                else:
                    total_session_errors = sum(error_counts.values())
                    sorted_session_errors = sorted(error_counts.items(), key=lambda item: item[1], reverse=True)
                    for error_name, count in sorted_session_errors:
                        percentage = (count / total_session_errors) * 100 if total_session_errors > 0 else 0
                        
                        row_inner_frame = ctk.CTkFrame(table_frame, fg_color="transparent", height=30)
                        row_inner_frame.grid(row=table_row_offset, column=0, columnspan=4, sticky="ew", pady=0)
                        row_inner_frame.grid_columnconfigure(0, weight=0, minsize=80)
                        row_inner_frame.grid_columnconfigure(1, weight=1)
                        row_inner_frame.grid_columnconfigure(2, weight=0, minsize=100)
                        row_inner_frame.grid_columnconfigure(3, weight=0, minsize=250)

                        ctk.CTkLabel(row_inner_frame, text=process_persian_text_for_matplotlib(str(count)), 
                                     font=("Vazirmatn", 11, "bold"), anchor="center").grid(row=0, column=0, padx=2, sticky="ew")
                        
                        progress_bar = ctk.CTkProgressBar(row_inner_frame, 
                                                          orientation="horizontal", mode="determinate", height=10, corner_radius=5,
                                                          fg_color="#E0E0E0", progress_color="#DC3545") # Red
                        progress_bar.set(percentage / 100)
                        progress_bar.grid(row=0, column=1, padx=2, sticky="ew")

                        ctk.CTkLabel(row_inner_frame, text=process_persian_text_for_matplotlib(f"{percentage:.1f}%"),
                                     font=("Vazirmatn", 11, "bold"), anchor="center").grid(row=0, column=2, padx=2, sticky="ew")
                        
                        ctk.CTkLabel(row_inner_frame, text=process_persian_text_for_matplotlib(error_name),
                                     font=("Vazirmatn", 11, "bold"), anchor="e", wraplength=200).grid(row=0, column=3, padx=2, sticky="ew")
                        
                        table_row_offset += 1
                row_idx += 1 # Advance main row_idx after adding the entire section

        elif current_mode == "session_segmentation":
            # Analysis for "Session Segmentation" mode
            segments_to_analyze = hourly_filter_data.get("segments", [])
            segment_results = {} # {(session_key, start_time, end_time): Counter(), ...}
            
            # Use original session names map for display purposes
            session_names_map = {
                'ny': 'Newyork', 'sydney': 'Sydney', 'tokyo': 'Tokyo', 'london': 'London'
            }

            if not segments_to_analyze:
                no_segments_label = ctk.CTkLabel(scrollable_content_frame, 
                                                text=process_persian_text_for_matplotlib("در حالت 'تفکیک سشن'، بازه‌ای برای آنالیز تعریف نشده است. لطفاً در تب 'ساعات ترید' بخش‌هایی را انتخاب کنید."),
                                                font=("Vazirmatn", 12), text_color="gray50", anchor="e", wraplength=500, justify="right")
                no_segments_label.grid(row=row_idx, column=0, pady=10, sticky="ew")
                row_idx += 1
                return


            # Initialize counters for all segments
            for seg in segments_to_analyze:
                segment_key = (seg['session_key'], seg['start'], seg['end'])
                segment_results[segment_key] = Counter()

            for trade in self.current_filtered_trades:
                trade_dt_obj = datetime.strptime(f"{trade['date']} {trade['time']}", '%Y-%m-%d %H:%M')
                
                for seg in segments_to_analyze:
                    if db_manager._is_trade_in_time_interval(trade_dt_obj, seg['start'], seg['end']):
                        if trade['errors']:
                            errors_in_trade = [err.strip() for err in trade['errors'].split(',') if err.strip()]
                            segment_key = (seg['session_key'], seg['start'], seg['end'])
                            for error in set(errors_in_trade):
                                segment_results[segment_key][error] += 1
                        # No break here, as a trade *could* fall into multiple segments if they overlap
                        # (though ideal segments typically don't overlap).

            ctk.CTkLabel(scrollable_content_frame, text=process_persian_text_for_matplotlib("آنالیز خطاها بر اساس تفکیک سشن"),
                         font=("Vazirmatn", 13, "bold"), text_color="#202124", anchor="e").grid(row=row_idx, column=0, pady=(10, 5), sticky="ew")
            row_idx += 1
            
            # Sort segments for consistent display
            sorted_segment_keys = sorted(segment_results.keys(), key=lambda x: (x[0], db_manager._time_to_minutes(x[1])))

            for segment_key in sorted_segment_keys:
                sess_key, start_time, end_time = segment_key
                error_counts = segment_results[segment_key]

                session_display_name = session_names_map.get(sess_key, sess_key.capitalize() if sess_key else "")
                segment_header_text = process_persian_text_for_matplotlib(f"بخش {session_display_name} ({start_time}-{end_time})")
                
                # Create a frame for the section (header button + table content)
                section_content_frame = ctk.CTkFrame(scrollable_content_frame, fg_color="transparent")
                section_content_frame.grid(row=row_idx, column=0, pady=(5, 10), sticky="ew")
                section_content_frame.grid_columnconfigure(0, weight=1)

                # Header button-like frame
                header_button_like_frame = ctk.CTkFrame(section_content_frame,
                                                         fg_color="#6F42C1", corner_radius=8, height=30)
                header_button_like_frame.pack(fill="x", pady=(0, 5))
                header_button_like_frame.pack_propagate(False)
                
                ctk.CTkLabel(header_button_like_frame, text=segment_header_text,
                             font=("Vazirmatn", 12, "bold"), text_color="white",
                             anchor="e", justify="right", wraplength=300).pack(expand=True, fill="both", padx=5, pady=0)


                # Now, create the table content for this section
                table_frame = ctk.CTkFrame(section_content_frame, fg_color="white", corner_radius=8)
                table_frame.pack(fill="both", expand=True, padx=10, pady=(0,5))
                table_frame.grid_columnconfigure(0, weight=0, minsize=80)
                table_frame.grid_columnconfigure(1, weight=1)
                table_frame.grid_columnconfigure(2, weight=0, minsize=100)
                table_frame.grid_columnconfigure(3, weight=0, minsize=250)

                table_row_offset = 0
                ctk.CTkLabel(table_frame, text=process_persian_text_for_matplotlib("تعداد"), font=("Vazirmatn", 11, "bold"), anchor="center").grid(row=table_row_offset, column=0, padx=2, pady=5, sticky="ew")
                ctk.CTkLabel(table_frame, text=process_persian_text_for_matplotlib("نمودار"), font=("Vazirmatn", 11, "bold"), anchor="w").grid(row=table_row_offset, column=1, padx=2, pady=5, sticky="ew")
                ctk.CTkLabel(table_frame, text=process_persian_text_for_matplotlib("درصد"), font=("Vazirmatn", 11, "bold"), anchor="center").grid(row=table_row_offset, column=2, padx=2, pady=5, sticky="ew")
                ctk.CTkLabel(table_frame, text=process_persian_text_for_matplotlib("خطا"), font=("Vazirmatn", 11, "bold"), anchor="e").grid(row=table_row_offset, column=3, padx=2, pady=5, sticky="ew")
                table_row_offset += 1

                if not error_counts:
                    ctk.CTkLabel(table_frame, text=process_persian_text_for_matplotlib("هیچ خطایی در این بخش یافت نشد."),
                                 font=("Vazirmatn", 11), text_color="gray60", anchor="e").grid(row=table_row_offset, column=0, columnspan=4, padx=20, pady=2, sticky="ew")
                else:
                    total_segment_errors = sum(error_counts.values())
                    sorted_segment_errors = sorted(error_counts.items(), key=lambda item: item[1], reverse=True)
                    for error_name, count in sorted_segment_errors:
                        percentage = (count / total_segment_errors) * 100 if total_segment_errors > 0 else 0
                        
                        row_inner_frame = ctk.CTkFrame(table_frame, fg_color="transparent", height=30)
                        row_inner_frame.grid(row=table_row_offset, column=0, columnspan=4, sticky="ew", pady=0)
                        row_inner_frame.grid_columnconfigure(0, weight=0, minsize=80)
                        row_inner_frame.grid_columnconfigure(1, weight=1)
                        row_inner_frame.grid_columnconfigure(2, weight=0, minsize=100)
                        row_inner_frame.grid_columnconfigure(3, weight=0, minsize=250)

                        ctk.CTkLabel(row_inner_frame, text=process_persian_text_for_matplotlib(str(count)), 
                                     font=("Vazirmatn", 11, "bold"), anchor="center").grid(row=0, column=0, padx=2, sticky="ew")
                        
                        progress_bar = ctk.CTkProgressBar(row_inner_frame, 
                                                          orientation="horizontal", mode="determinate", height=10, corner_radius=5,
                                                          fg_color="#E0E0E0", progress_color="#DC3545") # Red
                        progress_bar.set(percentage / 100)
                        progress_bar.grid(row=0, column=1, padx=2, sticky="ew")

                        ctk.CTkLabel(row_inner_frame, text=process_persian_text_for_matplotlib(f"{percentage:.1f}%"),
                                     font=("Vazirmatn", 11, "bold"), anchor="center").grid(row=0, column=2, padx=2, sticky="ew")
                        
                        ctk.CTkLabel(row_inner_frame, text=process_persian_text_for_matplotlib(error_name),
                                     font=("Vazirmatn", 11, "bold"), anchor="e", wraplength=200).grid(row=0, column=3, padx=2, sticky="ew")
                        
                        table_row_offset += 1
                row_idx += 1 # Advance main row_idx after adding the entire section


        elif current_mode in ["hourly_segmentation", "half_hourly_segmentation", "quarter_hourly_segmentation"]:
            # Analysis for Granular Segmentation modes
            intervals_to_analyze = hourly_filter_data.get("intervals", [])
            interval_results = {} # {(start_time, end_time): Counter(), ...}

            if not intervals_to_analyze:
                no_intervals_label = ctk.CTkLabel(scrollable_content_frame, 
                                                text=process_persian_text_for_matplotlib("در حالت تفکیک ساعتی/نیم‌ساعتی/یک‌ربعی، بازه‌ای برای آنالیز تعریف نشده است. لطفاً در تب 'ساعات ترید' بازه‌های زمانی را انتخاب کنید."),
                                                font=("Vazirmatn", 12), text_color="gray50", anchor="e", wraplength=500, justify="right")
                no_intervals_label.grid(row=row_idx, column=0, pady=10, sticky="ew")
                row_idx += 1
                return

            # Initialize counters for all intervals
            for interval in intervals_to_analyze:
                interval_key = (interval['start'], interval['end'])
                interval_results[interval_key] = Counter()

            for trade in self.current_filtered_trades:
                trade_dt_obj = datetime.strptime(f"{trade['date']} {trade['time']}", '%Y-%m-%d %H:%M')
                
                for interval in intervals_to_analyze:
                    if db_manager._is_trade_in_time_interval(trade_dt_obj, interval['start'], interval['end']):
                        if trade['errors']:
                            errors_in_trade = [err.strip() for err in trade['errors'].split(',') if err.strip()]
                            interval_key = (interval['start'], interval['end'])
                            for error in set(errors_in_trade):
                                interval_results[interval_key][error] += 1
                        # No break here, as a trade *could* fall into multiple intervals if they overlap (rare for proper granularity)

            granularity_display_name_map = {
                60: process_persian_text_for_matplotlib("تفکیک ساعتی"),
                30: process_persian_text_for_matplotlib("تفکیک نیم‌ساعتی"),
                15: process_persian_text_for_matplotlib("تفکیک یک‌ربعی")
            }
            granularity_text = granularity_display_name_map.get(hourly_filter_data.get("granularity"), process_persian_text_for_matplotlib("تفکیک زمانی"))

            ctk.CTkLabel(scrollable_content_frame, text=process_persian_text_for_matplotlib(f"آنالیز خطاها بر اساس {granularity_text}"),
                         font=("Vazirmatn", 13, "bold"), text_color="#202124", anchor="e").grid(row=row_idx, column=0, pady=(10, 5), sticky="ew")
            row_idx += 1

            # Sort intervals for consistent display
            sorted_interval_keys = sorted(interval_results.keys(), key=lambda x: db_manager._time_to_minutes(x[0]))


            for interval_key in sorted_interval_keys:
                start_time, end_time = interval_key
                error_counts = interval_results[interval_key]

                interval_header_text = process_persian_text_for_matplotlib(f"بازه {start_time}-{end_time}")
                
                # Create a frame for the section (header button + table content)
                section_content_frame = ctk.CTkFrame(scrollable_content_frame, fg_color="transparent")
                section_content_frame.grid(row=row_idx, column=0, pady=(5, 10), sticky="ew")
                section_content_frame.grid_columnconfigure(0, weight=1)

                # Header button-like frame
                header_button_like_frame = ctk.CTkFrame(section_content_frame,
                                                         fg_color="#17A2B8", corner_radius=8, height=30)
                header_button_like_frame.pack(fill="x", pady=(0, 5))
                header_button_like_frame.pack_propagate(False)

                ctk.CTkLabel(header_button_like_frame, text=interval_header_text,
                             font=("Vazirmatn", 12, "bold"), text_color="white",
                             anchor="e", justify="right", wraplength=300).pack(expand=True, fill="both", padx=5, pady=0)


                # Now, create the table content for this section
                table_frame = ctk.CTkFrame(section_content_frame, fg_color="white", corner_radius=8)
                table_frame.pack(fill="both", expand=True, padx=10, pady=(0,5))
                table_frame.grid_columnconfigure(0, weight=0, minsize=80)
                table_frame.grid_columnconfigure(1, weight=1)
                table_frame.grid_columnconfigure(2, weight=0, minsize=100)
                table_frame.grid_columnconfigure(3, weight=0, minsize=250)

                table_row_offset = 0
                ctk.CTkLabel(table_frame, text=process_persian_text_for_matplotlib("تعداد"), font=("Vazirmatn", 11, "bold"), anchor="center").grid(row=table_row_offset, column=0, padx=2, pady=5, sticky="ew")
                ctk.CTkLabel(table_frame, text=process_persian_text_for_matplotlib("نمودار"), font=("Vazirmatn", 11, "bold"), anchor="w").grid(row=table_row_offset, column=1, padx=2, pady=5, sticky="ew")
                ctk.CTkLabel(table_frame, text=process_persian_text_for_matplotlib("درصد"), font=("Vazirmatn", 11, "bold"), anchor="center").grid(row=table_row_offset, column=2, padx=2, pady=5, sticky="ew")
                ctk.CTkLabel(table_frame, text=process_persian_text_for_matplotlib("خطا"), font=("Vazirmatn", 11, "bold"), anchor="e").grid(row=table_row_offset, column=3, padx=2, pady=5, sticky="ew")
                table_row_offset += 1

                if not error_counts:
                    ctk.CTkLabel(table_frame, text=process_persian_text_for_matplotlib("هیچ خطایی در این بازه یافت نشد."),
                                 font=("Vazirmatn", 11), text_color="gray60", anchor="e").grid(row=table_row_offset, column=0, columnspan=4, padx=20, pady=2, sticky="ew")
                else:
                    total_interval_errors = sum(error_counts.values())
                    sorted_interval_errors = sorted(error_counts.items(), key=lambda item: item[1], reverse=True)
                    for error_name, count in sorted_interval_errors:
                        percentage = (count / total_interval_errors) * 100 if total_interval_errors > 0 else 0
                        
                        row_inner_frame = ctk.CTkFrame(table_frame, fg_color="transparent", height=30)
                        row_inner_frame.grid(row=table_row_offset, column=0, columnspan=4, sticky="ew", pady=0)
                        row_inner_frame.grid_columnconfigure(0, weight=0, minsize=80)
                        row_inner_frame.grid_columnconfigure(1, weight=1)
                        row_inner_frame.grid_columnconfigure(2, weight=0, minsize=100)
                        row_inner_frame.grid_columnconfigure(3, weight=0, minsize=250)

                        ctk.CTkLabel(row_inner_frame, text=process_persian_text_for_matplotlib(str(count)), 
                                     font=("Vazirmatn", 11, "bold"), anchor="center").grid(row=0, column=0, padx=2, sticky="ew")
                        
                        progress_bar = ctk.CTkProgressBar(row_inner_frame, 
                                                          orientation="horizontal", mode="determinate", height=10, corner_radius=5,
                                                          fg_color="#E0E0E0", progress_color="#DC3545") # Red
                        progress_bar.set(percentage / 100)
                        progress_bar.grid(row=0, column=1, padx=2, sticky="ew")

                        ctk.CTkLabel(row_inner_frame, text=process_persian_text_for_matplotlib(f"{percentage:.1f}%"),
                                     font=("Vazirmatn", 11, "bold"), anchor="center").grid(row=0, column=2, padx=2, sticky="ew")
                        
                        ctk.CTkLabel(row_inner_frame, text=process_persian_text_for_matplotlib(error_name),
                                     font=("Vazirmatn", 11, "bold"), anchor="e", wraplength=200).grid(row=0, column=3, padx=2, sticky="ew")
                        
                        table_row_offset += 1
                row_idx += 1 # Advance main row_idx after adding the entire section


        else:
            # Default/unknown mode
            ctk.CTkLabel(scrollable_content_frame, text=process_persian_text_for_matplotlib("حالت آنالیز ساعات ترید نامشخص است."),
                         font=("Vazirmatn", 12), text_color="gray50", anchor="center").grid(row=0, column=0, pady=50, sticky="nsew")

        scrollable_content_frame.update_idletasks()