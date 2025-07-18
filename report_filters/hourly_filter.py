# report_filters/hourly_filter.py

import customtkinter as ctk
import db_manager
from persian_chart_utils import process_persian_text_for_matplotlib
import tkinter as tk
from datetime import datetime, timedelta

class HourlyFilterFrame(ctk.CTkFrame):
    def __init__(self, master, on_change_callback=None, fg_color="transparent", **kwargs):
        super().__init__(master, fg_color=fg_color, **kwargs)
        self.on_change_callback = on_change_callback
        
        self.current_mode_var = ctk.StringVar(value="full_session") # Default mode
        self.segment_count_var = ctk.StringVar(value="2") # Default for segmentation

        self.granularity_var = ctk.StringVar(value=process_persian_text_for_matplotlib("ساعتی کامل")) # Default for custom_hour_minute mode
        self.selected_time_segments_vars = {} # Stores BooleanVars for custom hour/minute checkboxes
        self.all_custom_times_var = ctk.BooleanVar(value=True) # "همه" for custom selection

        # Store session details for internal use {session_key: {'start_utc': 'HH:MM', 'end_utc': 'HH:MM', 'start_display': 'HH:MM', 'end_display': 'HH:MM'}}
        self.available_session_details = {} 
        self.selected_session_keys = [] # List of session keys (e.g., ['ny', 'london']) from main filter

        self.grid_columnconfigure(0, weight=1) # Column for labels/radios
        self.grid_columnconfigure(1, weight=3) # Column for controls (sub-frames)

        # Hint Label: Shows that hours are filtered by selected sessions
        self.session_filter_hint_label = ctk.CTkLabel(self, 
                                                      text=process_persian_text_for_matplotlib("توجه: ساعات قابل انتخاب بر اساس سشن‌های انتخابی شما در تب 'سشن‌های معاملاتی' فیلتر شده‌اند."),
                                                      font=("Vazirmatn", 9, "italic"), text_color="gray50", anchor="e", wraplength=300)
        self.session_filter_hint_label.grid(row=0, column=0, columnspan=2, padx=5, pady=(5, 10), sticky="ew")

        # Radio Buttons for Selection Modes
        self.mode_label = ctk.CTkLabel(self, text=process_persian_text_for_matplotlib("حالت انتخاب ساعت:"), font=("Vazirmatn", 12))
        self.mode_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")

        self.radio_button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.radio_button_frame.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.radio_button_frame.grid_columnconfigure(0, weight=1) # Single column for radios

        self.radio_full_session = ctk.CTkRadioButton(self.radio_button_frame,
                                                    text=process_persian_text_for_matplotlib("سشن کامل"),
                                                    variable=self.current_mode_var,
                                                    value="full_session",
                                                    command=self._on_mode_change,
                                                    font=("Vazirmatn", 11),
                                                    radiobutton_width=20, radiobutton_height=20,
                                                    border_width_checked=6, border_color="#3B8ED0",
                                                    fg_color="#3B8ED0", hover_color="#1F6AA5")
        self.radio_full_session.grid(row=0, column=0, sticky="e", padx=10, pady=2)

        self.radio_session_segmentation = ctk.CTkRadioButton(self.radio_button_frame,
                                                            text=process_persian_text_for_matplotlib("تفکیک سشن"),
                                                            variable=self.current_mode_var,
                                                            value="session_segmentation",
                                                            command=self._on_mode_change,
                                                            font=("Vazirmatn", 11),
                                                            radiobutton_width=20, radiobutton_height=20,
                                                            border_width_checked=6, border_color="#3B8ED0",
                                                            fg_color="#3B8ED0", hover_color="#1F6AA5")
        self.radio_session_segmentation.grid(row=1, column=0, sticky="e", padx=10, pady=2)

        self.radio_custom_hour_minute = ctk.CTkRadioButton(self.radio_button_frame,
                                                          text=process_persian_text_for_matplotlib("تفکیک ساعت و دقیقه"),
                                                          variable=self.current_mode_var,
                                                          value="custom_hour_minute",
                                                          command=self._on_mode_change,
                                                          font=("Vazirmatn", 11),
                                                          radiobutton_width=20, radiobutton_height=20,
                                                          border_width_checked=6, border_color="#3B8ED0",
                                                          fg_color="#3B8ED0", hover_color="#1F6AA5")
        self.radio_custom_hour_minute.grid(row=2, column=0, sticky="e", padx=10, pady=2)

        # --- Sub-frames for each mode ---
        self.mode_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.mode_content_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky="nsew")
        self.mode_content_frame.grid_columnconfigure(0, weight=1)
        self.mode_content_frame.grid_rowconfigure(0, weight=1)


        # Full Session Content
        self.full_session_frame = ctk.CTkFrame(self.mode_content_frame, fg_color="transparent")
        self.full_session_label = ctk.CTkLabel(self.full_session_frame, 
                                               text=process_persian_text_for_matplotlib("در این حالت، کل بازه سشن(های) انتخاب شده در تب 'سشن‌های معاملاتی' در نظر گرفته می‌شود."),
                                               font=("Vazirmatn", 11), wraplength=350, anchor="e")
        self.full_session_label.pack(padx=10, pady=20)


        # Session Segmentation Content
        self.session_segmentation_frame = ctk.CTkFrame(self.mode_content_frame, fg_color="transparent")
        self.session_segmentation_frame.grid_columnconfigure(0, weight=1)
        self.session_segmentation_frame.grid_columnconfigure(1, weight=1)

        self.segment_count_label = ctk.CTkLabel(self.session_segmentation_frame, 
                                                 text=process_persian_text_for_matplotlib("تعداد قسمت‌ها برای هر سشن:"),
                                                 font=("Vazirmatn", 11))
        self.segment_count_label.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        self.segment_count_optionmenu = ctk.CTkOptionMenu(self.session_segmentation_frame,
                                                          variable=self.segment_count_var,
                                                          values=["2", "3", "4"], # Updated values
                                                          command=self._on_segment_count_change,
                                                          font=("Vazirmatn", 11))
        self.segment_count_optionmenu.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Placeholder for calculated segments display (optional, but useful for user feedback)
        self.calculated_segments_display = ctk.CTkLabel(self.session_segmentation_frame,
                                                        text=process_persian_text_for_matplotlib("بخش‌های محاسبه شده:"),
                                                        font=("Vazirmatn", 10, "italic"), text_color="gray50", wraplength=350, anchor="e", justify="right")
        self.calculated_segments_display.grid(row=1, column=0, columnspan=2, padx=5, pady=(5,0), sticky="ew")


        # Custom Hour/Minute Content (New Implementation)
        self.custom_hour_minute_frame = ctk.CTkFrame(self.mode_content_frame, fg_color="transparent")
        self.custom_hour_minute_frame.grid_columnconfigure(0, weight=1)
        self.custom_hour_minute_frame.grid_columnconfigure(1, weight=1)
        
        self.granularity_label = ctk.CTkLabel(self.custom_hour_minute_frame,
                                              text=process_persian_text_for_matplotlib("تفکیک زمان:"),
                                              font=("Vazirmatn", 11))
        self.granularity_label.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        self.granularity_optionmenu = ctk.CTkOptionMenu(self.custom_hour_minute_frame,
                                                       variable=self.granularity_var,
                                                       values=[process_persian_text_for_matplotlib("ساعتی کامل"),
                                                               process_persian_text_for_matplotlib("نیم‌ساعتی"),
                                                               process_persian_text_for_matplotlib("۱۵ دقیقه‌ای")],
                                                       command=self._on_granularity_change,
                                                       font=("Vazirmatn", 11))
        self.granularity_optionmenu.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Frame for actual time checkboxes
        self.time_checkbox_scroll_frame = ctk.CTkScrollableFrame(self.custom_hour_minute_frame, fg_color="transparent", height=200)
        self.time_checkbox_scroll_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        self.time_checkbox_scroll_frame.grid_columnconfigure(0, weight=1)
        self.time_checkbox_scroll_frame.grid_columnconfigure(1, weight=1)
        self.time_checkbox_scroll_frame.grid_columnconfigure(2, weight=1) # For more columns if needed

        self.all_custom_times_checkbox = ctk.CTkCheckBox(self.custom_hour_minute_frame,
                                                          text=process_persian_text_for_matplotlib("انتخاب/لغو همه"),
                                                          variable=self.all_custom_times_var,
                                                          command=self._toggle_all_custom_times,
                                                          font=("Vazirmatn", 11, "bold"),
                                                          fg_color=("blue", "blue"),
                                                          checkbox_width=18, checkbox_height=18,
                                                          border_color=("gray60", "gray40"),
                                                          checkmark_color="white")
        self.all_custom_times_checkbox.grid(row=2, column=0, columnspan=2, sticky="e", padx=10, pady=5)
        
        # Removed the "Selected Ranges" label as per user request
        # self.selected_custom_times_display = ctk.CTkLabel(self.custom_hour_minute_frame,
        #                                                   text=process_persian_text_for_matplotlib("بازه(های) انتخابی:"),
        #                                                   font=("Vazirmatn", 10, "italic"), text_color="gray50", wraplength=350, anchor="e", justify="right")
        # self.selected_custom_times_display.grid(row=3, column=0, columnspan=2, padx=5, pady=(5,0), sticky="ew")


        # Initial display setup
        self._show_current_mode_frame()
        
        # Initial load, this should be called by ReportSelectionWindow to pass current session selections
        self.reload_hourly_data(selected_sessions_from_main=None, initial_load=True) # Pass None initially, will be updated by RSWindow

    def _on_mode_change(self):
        self._show_current_mode_frame()
        self._update_calculated_segments_display() # Update segmentation display when mode changes
        self._update_custom_time_checkboxes() # Update custom time checkboxes when mode changes
        if self.on_change_callback:
            self.on_change_callback()

    def _on_segment_count_change(self, new_value):
        self._update_calculated_segments_display() # Update segmentation display when segment count changes
        if self.on_change_callback:
            self.on_change_callback()
    
    def _on_granularity_change(self, new_value):
        self._update_custom_time_checkboxes() # Re-populate checkboxes based on new granularity
        if self.on_change_callback:
            self.on_change_callback()

    def _on_custom_time_checkbox_change(self, time_segment_str):
        # Update 'Select/Deselect All' checkbox based on individual checkbox states
        if not self.selected_time_segments_vars[time_segment_str].get():
            self.all_custom_times_var.set(False)
        elif all(var.get() for var in self.selected_time_segments_vars.values()):
            self.all_custom_times_var.set(True)
        
        # Removed _update_selected_custom_times_display() as the label is removed
        if self.on_change_callback:
            self.on_change_callback()

    def _toggle_all_custom_times(self):
        is_all_selected = self.all_custom_times_var.get()
        for time_segment_str, var in self.selected_time_segments_vars.items():
            var.set(is_all_selected)
        # Removed _update_selected_custom_times_display() as the label is removed
        if self.on_change_callback:
            self.on_change_callback()

    def _show_current_mode_frame(self):
        # Hide all content frames
        self.full_session_frame.grid_forget()
        self.session_segmentation_frame.grid_forget()
        self.custom_hour_minute_frame.grid_forget()

        # Show the selected mode's frame
        current_mode = self.current_mode_var.get()
        if current_mode == "full_session":
            self.full_session_frame.grid(row=0, column=0, sticky="nsew")
        elif current_mode == "session_segmentation":
            self.session_segmentation_frame.grid(row=0, column=0, sticky="nsew")
        elif current_mode == "custom_hour_minute":
            self.custom_hour_minute_frame.grid(row=0, column=0, sticky="nsew")

    def reload_hourly_data(self, selected_sessions_from_main=None, initial_load=False):
        """
        This function reloads hourly filter options,
        especially based on the selected sessions from ReportSelectionWindow.
        """
        user_tz_name = db_manager.get_default_timezone()
        self.available_session_details = db_manager.get_session_times_with_display_utc(user_tz_name)

        if selected_sessions_from_main:
            self.selected_session_keys = selected_sessions_from_main
            
            if selected_sessions_from_main == "همه":
                sessions_text = process_persian_text_for_matplotlib("همه سشن‌ها")
                active_sessions_for_display = list(self.available_session_details.values())
            elif isinstance(selected_sessions_from_main, list) and selected_sessions_from_main:
                active_sessions_for_display = [self.available_session_details[key] for key in self.selected_session_keys if key in self.available_session_details]
                display_sessions_texts = []
                # Define local session_names_map inside this function as it's used for display logic
                local_session_names_map = {
                    'ny': 'نیویورک', 'sydney': 'سیدنی', 'tokyo': 'توکیو', 'london': 'لندن'
                }
                for details in active_sessions_for_display:
                    session_key_for_display = next((k for k,v in self.available_session_details.items() if v == details), None)
                    session_display_name = local_session_names_map.get(session_key_for_display, session_key_for_display.capitalize() if session_key_for_display else "")
                    display_sessions_texts.append(f"{session_display_name} ({details['start_display']} - {details['end_display']})")
                sessions_text = process_persian_text_for_matplotlib(", ".join(display_sessions_texts))
            else:
                sessions_text = process_persian_text_for_matplotlib("هیچ سشنی انتخاب نشده است.")
                active_sessions_for_display = []
            
            self.session_filter_hint_label.configure(text=process_persian_text_for_matplotlib(f"توجه: ساعات قابل انتخاب بر اساس سشن‌های انتخابی شما ({sessions_text}) در تب 'سشن‌های معاملاتی' فیلتر شده‌اند."))
        else:
            self.selected_session_keys = []
            self.session_filter_hint_label.configure(text=process_persian_text_for_matplotlib("توجه: ساعات قابل انتخاب بر اساس سشن‌های انتخابی شما در تب 'سشن‌های معاملاتی' فیلتر شده‌اند."))
            active_sessions_for_display = []

        # Update the calculated segments display based on new session data
        self._update_calculated_segments_display()
        # Update custom time checkboxes based on new session data
        self._update_custom_time_checkboxes()

        # Do NOT trigger on_change_callback here.
        # It will be triggered by ReportSelectionWindow after all filters are initialized,
        # or by user interaction with the radio buttons.

    def _update_calculated_segments_display(self):
        """Calculates and updates the display for segmented sessions."""
        if self.current_mode_var.get() == "session_segmentation":
            segments_to_show = []
            try:
                num_segments = int(self.segment_count_var.get())
                if num_segments < 2: # Ensure at least 2 segments for meaningful split
                    num_segments = 2

                sessions_to_segment = []
                if self.selected_session_keys == "همه":
                    sessions_to_segment = list(self.available_session_details.values())
                elif isinstance(self.selected_session_keys, list) and self.selected_session_keys:
                    sessions_to_segment = [self.available_session_details[key] for key in self.selected_session_keys if key in self.available_session_details]
                
                if not sessions_to_segment:
                    self.calculated_segments_display.configure(text=process_persian_text_for_matplotlib("لطفاً در تب 'سشن‌های معاملاتی' حداقل یک سشن را انتخاب کنید."))
                    return

                # Define local session names map for display purposes
                local_session_names_map = {
                    'ny': 'نیویورک', 'sydney': 'سیدنی', 'tokyo': 'توکیو', 'london': 'لندن'
                }

                for session in sessions_to_segment:
                    start_time_str = session['start_display']
                    end_time_str = session['end_display']
                    
                    session_key_for_display = next((k for k, v in self.available_session_details.items() if v == session), None)
                    session_name = local_session_names_map.get(session_key_for_display, session_key_for_display.capitalize() if session_key_for_display else "")


                    start_minutes = self._time_to_minutes(start_time_str)
                    end_minutes = self._time_to_minutes(end_time_str)

                    # Handle overnight sessions (e.g., 23:00 - 03:00)
                    if end_minutes <= start_minutes:
                        end_minutes += (24 * 60) # Add a day's worth of minutes

                    total_duration = end_minutes - start_minutes
                    segment_duration = total_duration / num_segments

                    segment_texts = []
                    for i in range(num_segments):
                        segment_start_minutes = start_minutes + (i * segment_duration)
                        segment_end_minutes = start_minutes + ((i + 1) * segment_duration)
                        
                        # Ensure segments don't go past actual end time for the last segment
                        if i == num_segments - 1:
                            segment_end_minutes = end_minutes
                            
                        segment_start_time_str = self._minutes_to_time(int(segment_start_minutes))
                        segment_end_time_str = self._minutes_to_time(int(segment_end_minutes))
                        segment_texts.append(f"{segment_start_time_str}-{segment_end_time_str}")
                    
                    segments_to_show.append(f"{session_name}: {process_persian_text_for_matplotlib(', ').join(segment_texts)}")
                
                self.calculated_segments_display.configure(text=process_persian_text_for_matplotlib("بخش‌های محاسبه شده:") + "\n" + process_persian_text_for_matplotlib('\n').join(segments_to_show))

            except ValueError:
                self.calculated_segments_display.configure(text=process_persian_text_for_matplotlib("خطا در محاسبه. لطفاً مقادیر معتبر وارد کنید."))
            except Exception as e:
                self.calculated_segments_display.configure(text=process_persian_text_for_matplotlib(f"خطا در تفکیک: {e}"))
        else:
            self.calculated_segments_display.configure(text="")

    def _update_custom_time_checkboxes(self):
        """Populates or updates the checkboxes for custom hour/minute selection based on granularity and selected sessions."""
        # Clear existing checkboxes
        for widget in self.time_checkbox_scroll_frame.winfo_children():
            widget.destroy()
        
        # Store previous selections to restore them after repopulating
        previously_selected_segments = [s for s, var in self.selected_time_segments_vars.items() if var.get()]
        self.selected_time_segments_vars = {}

        if self.current_mode_var.get() != "custom_hour_minute":
            # Removed selected_custom_times_display update as the label is removed
            return

        active_session_intervals_minutes = [] # List of (start_minutes, end_minutes) for selected sessions in local timezone
        
        if self.selected_session_keys == "همه":
            sessions_to_use = list(self.available_session_details.values())
        elif isinstance(self.selected_session_keys, list) and self.selected_session_keys:
            sessions_to_use = [self.available_session_details[key] for key in self.selected_session_keys if key in self.available_session_details]
        else:
            # Display a message if no sessions are selected
            no_session_label = ctk.CTkLabel(self.time_checkbox_scroll_frame,
                                            text=process_persian_text_for_matplotlib("لطفاً در تب 'سشن‌های معاملاتی' حداقل یک سشن را انتخاب کنید."),
                                            font=("Vazirmatn", 11), text_color="gray50", anchor="e", wraplength=300)
            no_session_label.grid(row=0, column=0, columnspan=3, padx=5, pady=20, sticky="ew")
            self.all_custom_times_checkbox.configure(state="disabled")
            # Removed selected_custom_times_display update as the label is removed
            return

        for session in sessions_to_use:
            start_minutes = self._time_to_minutes(session['start_display'])
            end_minutes = self._time_to_minutes(session['end_display'])
            if end_minutes <= start_minutes: # Handle overnight sessions
                end_minutes += (24 * 60)
            active_session_intervals_minutes.append((start_minutes, end_minutes))
        
        if not active_session_intervals_minutes:
            no_session_label = ctk.CTkLabel(self.time_checkbox_scroll_frame,
                                            text=process_persian_text_for_matplotlib("هیچ سشنی برای نمایش ساعات پیدا نشد."),
                                            font=("Vazirmatn", 11), text_color="gray50", anchor="e", wraplength=300)
            no_session_label.grid(row=0, column=0, columnspan=3, padx=5, pady=20, sticky="ew")
            self.all_custom_times_checkbox.configure(state="disabled")
            # Removed selected_custom_times_display update as the label is removed
            return

        self.all_custom_times_checkbox.configure(state="normal")
        
        granularity_value_map = {
            process_persian_text_for_matplotlib("ساعتی کامل"): 60,
            process_persian_text_for_matplotlib("نیم‌ساعتی"): 30,
            process_persian_text_for_matplotlib("۱۵ دقیقه‌ای"): 15
        }
        step_minutes = granularity_value_map.get(self.granularity_var.get(), 60)

        # Generate unique time segments within the active session intervals
        all_possible_segments = set()
        
        # Combine all session intervals into a single sorted list of events
        events = []
        for s_start, s_end in active_session_intervals_minutes:
            events.append((s_start, 1)) # 1 for start
            events.append((s_end, -1)) # -1 for end
        events.sort() # Sort by time

        active_count = 0
        current_intersection_start = -1
        
        # This logic correctly finds continuous active intervals considering overlaps and gaps
        continuous_active_intervals = []
        for time_point, event_type in events:
            if event_type == 1: # Start of an interval
                if active_count == 0:
                    current_intersection_start = time_point
                active_count += 1
            else: # End of an interval
                active_count -= 1
                if active_count == 0 and current_intersection_start != -1:
                    continuous_active_intervals.append((current_intersection_start, time_point))
                    current_intersection_start = -1
        
        # Now, split these continuous active intervals by granularity
        for interval_start, interval_end in continuous_active_intervals:
            current_time = interval_start
            while current_time < interval_end:
                segment_start_minutes = current_time
                segment_end_minutes = min(current_time + step_minutes, interval_end)
                
                # Format as "HH:MM-HH:MM"
                segment_str = f"{self._minutes_to_time(int(segment_start_minutes))}-{self._minutes_to_time(int(segment_end_minutes))}"
                all_possible_segments.add((segment_start_minutes, segment_end_minutes, segment_str))
                current_time += step_minutes
        
        sorted_segments = sorted(list(all_possible_segments))

        col_count = 3 # Number of columns for checkboxes
        row_idx = 0
        col_idx = 0
        all_selected_after_reload = True # Track if all should be checked

        for start_min, end_min, segment_str in sorted_segments:
            # Check if this segment was previously selected
            is_checked = segment_str in previously_selected_segments 
            var = ctk.BooleanVar(value=is_checked) 
            self.selected_time_segments_vars[segment_str] = var

            checkbox = ctk.CTkCheckBox(self.time_checkbox_scroll_frame,
                                       text=process_persian_text_for_matplotlib(segment_str),
                                       variable=var,
                                       command=lambda ts=segment_str: self._on_custom_time_checkbox_change(ts),
                                       font=("Vazirmatn", 11),
                                       checkbox_width=18, checkbox_height=18,
                                       border_color=("gray60", "gray40"),
                                       checkmark_color="white")
            checkbox.grid(row=row_idx, column=col_idx, sticky="e", padx=5, pady=2) # Right-aligned for Persian text

            col_idx += 1
            if col_idx >= col_count:
                col_idx = 0
                row_idx += 1
            
            if not is_checked: # If any checkbox is not checked, 'select all' should be unchecked
                all_selected_after_reload = False

        self.all_custom_times_var.set(all_selected_after_reload)
        # Removed _update_selected_custom_times_display() as the label is removed


    def _time_to_minutes(self, time_str):
        """Converts 'HH:MM' string to total minutes from midnight."""
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

    def _minutes_to_time(self, total_minutes):
        """Converts total minutes from midnight to 'HH:MM' string (handles values > 24 hours)."""
        total_minutes = total_minutes % (24 * 60) # Wrap around for display if past midnight
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h:02d}:{m:02d}"

    def get_selection(self):
        current_mode = self.current_mode_var.get()
        selection_data = {"mode": current_mode}

        if current_mode == "full_session":
            selection_data["sessions"] = self.selected_session_keys
            
        elif current_mode == "session_segmentation":
            segments_list = []
            try:
                num_segments = int(self.segment_count_var.get())
                if num_segments < 2:
                    num_segments = 2
                
                sessions_to_segment = []
                if self.selected_session_keys == "همه":
                    sessions_to_segment = list(self.available_session_details.values())
                elif isinstance(self.selected_session_keys, list) and self.selected_session_keys:
                    sessions_to_segment = [self.available_session_details[key] for key in self.selected_session_keys if key in self.available_session_details]

                # Define local session names map for display purposes (though not used here, useful for context)
                local_session_names_map = {
                    'ny': 'نیویورک', 'sydney': 'سیدنی', 'tokyo': 'توکیو', 'london': 'لندن'
                }

                for session in sessions_to_segment:
                    start_time_str = session['start_display']
                    end_time_str = session['end_display']

                    start_minutes = self._time_to_minutes(start_time_str)
                    end_minutes = self._time_to_minutes(end_time_str)

                    if end_minutes <= start_minutes:
                        end_minutes += (24 * 60)

                    total_duration = end_minutes - start_minutes
                    segment_duration = total_duration / num_segments

                    for i in range(num_segments):
                        segment_start_minutes = start_minutes + (i * segment_duration)
                        segment_end_minutes = start_minutes + ((i + 1) * segment_duration)
                        if i == num_segments - 1: # Ensure the last segment exactly ends at session end
                            segment_end_minutes = end_minutes

                        # Get session_key to pass along with segment data
                        session_key_for_segment = next((k for k, v in self.available_session_details.items() if v == session), None)

                        segments_list.append({
                            "session_key": session_key_for_segment, # To identify which session this segment belongs to
                            "start": self._minutes_to_time(int(segment_start_minutes)),
                            "end": self._minutes_to_time(int(segment_end_minutes))
                        })
                selection_data["segments"] = segments_list
                selection_data["segment_count"] = num_segments

            except ValueError:
                selection_data["segments"] = []
                selection_data["segment_count"] = None
            except Exception as e:
                print(f"Error getting session segmentation: {e}")
                selection_data["segments"] = []
                selection_data["segment_count"] = None

        elif current_mode == "custom_hour_minute":
            selected_custom_intervals = []
            granularity_display_name = self.granularity_var.get()
            
            # Convert persian granularity name back to internal value if needed
            granularity_value_map_reverse = {
                process_persian_text_for_matplotlib("ساعتی کامل"): 60,
                process_persian_text_for_matplotlib("نیم‌ساعتی"): 30,
                process_persian_text_for_matplotlib("۱۵ دقیقه‌ای"): 15
            }
            granularity_internal_value = granularity_value_map_reverse.get(granularity_display_name, 60)

            for segment_str, var in self.selected_time_segments_vars.items():
                if var.get():
                    # segment_str is like "HH:MM-HH:MM"
                    start_str, end_str = segment_str.split('-')
                    selected_custom_intervals.append({"start": start_str, "end": end_str})
            
            selection_data["custom_intervals"] = selected_custom_intervals
            selection_data["granularity"] = granularity_internal_value
        
        return selection_data

    def set_selection(self, mode, segments=None, custom_intervals=None, granularity=None): # Updated parameter custom_range to custom_intervals
        self.current_mode_var.set(mode)
        self._show_current_mode_frame()
        
        if mode == "session_segmentation" and segments is not None:
            if isinstance(segments, int): # segments can be segment_count for future use
                self.segment_count_var.set(str(segments))
            # Future: If segments is a list of actual segments, we might need to recreate UI based on that
        elif mode == "custom_hour_minute" and custom_intervals is not None: # Updated parameter custom_range to custom_intervals
            # This part is complex because it needs to set multiple checkboxes
            # For now, we only set the granularity, re-populating checkboxes on _update_custom_time_checkboxes
            granularity_display_name_map = {
                60: process_persian_text_for_matplotlib("ساعتی کامل"),
                30: process_persian_text_for_matplotlib("نیم‌ساعتی"),
                15: process_persian_text_for_matplotlib("۱۵ دقیقه‌ای")
            }
            if granularity in granularity_display_name_map:
                self.granularity_var.set(granularity_display_name_map[granularity])
            
            # Here, we need to ensure the checkboxes are created first, then set their states.
            # Calling _update_custom_time_checkboxes will recreate them, and previously_selected_segments logic
            # will handle setting their states based on custom_intervals
            self._update_custom_time_checkboxes() # Ensure checkboxes are populated based on granularity
            
            # Now, explicitly set the checked state based on custom_intervals
            for interval_data in custom_intervals:
                interval_str = f"{interval_data['start']}-{interval_data['end']}"
                if interval_str in self.selected_time_segments_vars:
                    self.selected_time_segments_vars[interval_str].set(True)
            
            # After setting, update the 'select all' checkbox state
            if all(var.get() for var in self.selected_time_segments_vars.values()):
                self.all_custom_times_var.set(True)
            else:
                self.all_custom_times_var.set(False)

        
        self._update_calculated_segments_display() # Update display after setting selection
        # No need to call on_change_callback here directly.